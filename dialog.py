# dialog.py

import os
import json
import threading
import asyncio
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, Qt, QMetaObject, QTimer
from PyQt6.QtWidgets import QMenu, QTableWidgetItem, QApplication, QTableWidget, QAbstractItemView
from main_ui import MGMT_MENU_STYLE, BTN_RED, BTN_ORANGE
from engine.kuc_client import KucoinClient
 
class MainDialog(QObject):
    """
    MainTradingUI болон арын логикийг холбогч Controller класс.
    Товчлуур болон дата урсгалыг энд нэгтгэнэ.
    """
    log_signal = pyqtSignal(str)
    # UI Thread-тэй аюулгүй харилцах гүүр сигналууд
    price_bridge = pyqtSignal(dict)
    balance_bridge = pyqtSignal(dict)
    net_status_bridge = pyqtSignal(dict)

    def __init__(self, ui_instance):
        super().__init__()
        self.ui = ui_instance
        self.file_lock = threading.RLock()
        self.active_symbols = {}
        self.symbol_to_row = {} # Symbol -> Row mapping
        self.initial_mid_prices = {} # To store initial mid price for Real% calculation
        
        # Үнийн кэш
        self.ws_bids = {}
        self.ws_asks = {}
        self.all_data = [] # Market data cache

        # 1. KuCoin Client эхлүүлэх
        self.kuc = KucoinClient()
        self.exchange = self.kuc.exchange
        
        # 2. Клиентийн сигналуудыг Bridge-ээр дамжуулж UI thread рүү шидэх
        self.kuc.price_signal.connect(lambda data: self.price_bridge.emit(data))
        self.kuc.balance_signal.connect(lambda data: self.balance_bridge.emit(data))
        self.kuc.net_status_signal.connect(lambda data: self.net_status_bridge.emit(data))

        self.price_bridge.connect(self._on_price_update)
        self.balance_bridge.connect(self._on_balance_update)
        self.net_status_bridge.connect(self._on_net_status_update)
        
        self.kuc.error_signal.connect(lambda msg: self.log_signal.emit(f"❌ ERROR DETECTED:\n{msg}"))
        
        # WebSocket-ийг шууд эхлүүлэх (Жишээ болгож BTC/USDT)
        self.kuc.start_market_stream()

        # Таймерын утгуудыг тохируулах
        self.bal_countdown = 5
        self.sync_countdown = 60
        self.ui_tick_timer = QTimer()
        self.ui_tick_timer.timeout.connect(self._ui_heartbeat)
        self.ui_tick_timer.start(1000) # 1 секунд тутам

        # 3. UI Сигнал холболтууд
        self._wire_ui()
        self._load_active_trades()

        # 4. Системийн авто-шинэчлэл (1 минут тутамд)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._on_system_heartbeat)
        self.refresh_timer.start(60000) # 60,000 ms = 1 минут

        # 5. Баланс авто-шинэчлэл (5 секунд тутамд)
        self.balance_timer = QTimer()
        self.balance_timer.timeout.connect(self.start_fetch)
        self.balance_timer.start(5000) # 5,000 ms = 5 секунд

    def _wire_ui(self):
        """UI-ийн товчлууруудыг логик функцүүдтэй холбох."""
        # Лог мессеж хүлээн авах
        self.log_signal.connect(self._append_log_to_ui)

        # Buttons (BUY, SELL, MGMT, START)
        self.ui.buy_btn.clicked.connect(lambda: self._handle_action("BUY"))
        self.ui.sell_btn.clicked.connect(lambda: self._handle_action("SELL"))
        self.ui.mgmt_btn.clicked.connect(self._show_mgmt_menu)
        self.ui.hide_btn.clicked.connect(self._show_hide_menu)
        self.ui.start_btn.clicked.connect(self._toggle_strategy)

        # Copy Buttons wiring
        self.ui.market_copy_btn.clicked.connect(lambda: self._copy_table_to_clipboard(self.ui.market_table))
        self.ui.balance_copy_btn.clicked.connect(lambda: self._copy_table_to_clipboard(self.ui.balance_table))
        self.ui.history_copy_btn.clicked.connect(self._copy_history_tab_data)
        self.ui.logs_copy_btn.clicked.connect(self._copy_logs)

        # Market Table Interaction (Зоос сонгох)
        self.ui.market_table.itemClicked.connect(self._on_market_select)
        self.ui.market_table.horizontalHeader().sectionClicked.connect(self._on_market_header_clicked)
        self.ui.market_table.horizontalHeader().sortIndicatorChanged.connect(lambda: self._reindex_table(self.ui.market_table))

    # --- Logic Interface (Бусад логикуудын хайдаг функцууд) ---
    
    def _fmt(self, val, precision=8, sign=False):
        """Тоон утгыг форматлаж, арын илүүдэл 0-үүдийг хасна."""
        fmt_str = f"{val:+.{precision}f}" if sign else f"{val:.{precision}f}"
        return fmt_str.rstrip('0').rstrip('.')

    def _set_num_item(self, table, row, col, val, precision=8, sign=False):
        """Тоон утгыг хүснэгтийн нүдэнд эрэмбэлэлт алдагдуулахгүйгээр оноох."""
        item = table.item(row, col)
        if not item:
            item = QTableWidgetItem()
            table.setItem(row, col, item)
        item.setData(Qt.ItemDataRole.DisplayRole, self._fmt(val, precision, sign))
        item.setData(Qt.ItemDataRole.EditRole, float(val))
        return item

    def _reindex_table(self, table):
        """Хүснэгтийн эрэмбэлэлтийн дараа # баганыг 1, 2, 3 гэж дахин дугаарлах."""
        sorting_enabled = table.isSortingEnabled()
        table.setSortingEnabled(False)
        for r in range(table.rowCount()):
            item = table.item(r, 0)
            if item:
                item.setData(Qt.ItemDataRole.DisplayRole, str(r + 1))
                item.setData(Qt.ItemDataRole.EditRole, r + 1)
        table.setSortingEnabled(sorting_enabled)

    @pyqtSlot(dict)
    def _on_price_update(self, data):
        """Client-ээс ирсэн шинэ үнийг кэшлэх болон UI хүснэгтийг шинэчлэх."""
        sym = data['symbol']
        self.ws_bids[sym] = data['bid']
        self.ws_asks[sym] = data['ask']

        table = self.ui.market_table
        bid = data['bid']
        ask = data['ask']
        
        # Sorting идэвхтэй үед дата шинэчлэх нь UI-г гацаадаг тул түр зогсооно
        sorting_was_enabled = table.isSortingEnabled()
        table.setSortingEnabled(False)
        try:
            # Хэрэв энэ зоос хүснэгтэд байхгүй бол шинээр мөр нэмнэ
            if sym not in self.symbol_to_row:
                row = table.rowCount()
                table.insertRow(row)
                self.symbol_to_row[sym] = row
                
                # Анхны Mid Price хадгалах (Real% тооцоолох)
                self.initial_mid_prices[sym] = (bid + ask) / 2
                # Анхны утгуудыг оноох
                row_item = QTableWidgetItem()
                row_item.setData(Qt.ItemDataRole.EditRole, row + 1)
                table.setItem(row, 0, row_item)
                
                table.setItem(row, 1, QTableWidgetItem(sym.replace('/USDT', '')))
                # Бусад багануудыг хоосон Item-аар дүүргэх
                for i in range(2, 10):
                    table.setItem(row, i, QTableWidgetItem("-"))

            row = self.symbol_to_row[sym]
            # Spread тооцоолох: ((Ask - Bid) / Bid) * 100
            spread = ((ask - bid) / bid * 100) if bid > 0 else 0

            # Real% тооцоолох (Ask/Bid дундаж үнээр)
            current_mid = (bid + ask) / 2
            real_change = 0.0
            if sym in self.initial_mid_prices and self.initial_mid_prices[sym] > 0:
                real_change = ((current_mid - self.initial_mid_prices[sym]) / self.initial_mid_prices[sym]) * 100

            # Лимитүүдийг авах
            min_amount = data.get('min_amount', 0.0)
            # Min $ тооцоолол
            actual_min_usdt = min_amount * bid if bid > 0 else 0.0

            # Хүснэгтийн нүднүүдийг тоон утгаар шинэчлэх
            self._set_num_item(table, row, 2, bid)
            self._set_num_item(table, row, 3, ask)
            self._set_num_item(table, row, 4, spread) # Spread%
            self._set_num_item(table, row, 5, actual_min_usdt) # Min $
            self._set_num_item(table, row, 6, data['volume']) # Vol
            
            real_change_item = self._set_num_item(table, row, 7, real_change, sign=True)
            
            # 24H баганыг шинэчлэх (Хэрэв өгөгдөл ирсэн бол)
            change_val = data.get('change')
            if change_val is not None:
                change_item = self._set_num_item(table, row, 8, change_val, sign=True)
                
                # Үнийн өөрчлөлтөөс хамаарч өнгө солих
                if change_val > 0:
                    change_item.setForeground(Qt.GlobalColor.green)
                elif change_val < 0:
                    change_item.setForeground(Qt.GlobalColor.red)
                else:
                    change_item.setForeground(Qt.GlobalColor.white)

            # Limit багана - Хамгийн бага арилжих ширхэгийн тоо (Coin amount)
            self._set_num_item(table, row, 9, min_amount)

        finally:
            table.setSortingEnabled(sorting_was_enabled)
        
        # Market Totals update (External table)
        self._update_market_totals()

    def _update_market_totals(self):
        """Market хүснэгтийн Real% болон 24% нийлбэрийг тооцоолох."""
        table = self.ui.market_table
        footer = self.ui.market_total_table
        t_vol = 0.0
        total_real = 0.0
        total_24h = 0.0
        
        def safe_float(v):
            try:
                return float(v) if v != "-" else 0.0
            except (ValueError, TypeError):
                return 0.0

        for r in range(table.rowCount()):
            # Column indices: Vol (6), Real% (7), 24% (8)
            v_val = table.item(r, 6).data(Qt.ItemDataRole.EditRole) if table.item(r, 6) else 0
            re_val = table.item(r, 7).data(Qt.ItemDataRole.EditRole) if table.item(r, 7) else 0
            c_val = table.item(r, 8).data(Qt.ItemDataRole.EditRole) if table.item(r, 8) else 0
            
            t_vol += safe_float(v_val)
            total_real += safe_float(re_val)
            total_24h += safe_float(c_val)

        # Footer-ийг шинэчлэх
        footer.setItem(0, 1, QTableWidgetItem("TOTAL"))
        footer.item(0, 1).setForeground(Qt.GlobalColor.yellow)
        self._set_num_item(footer, 0, 6, t_vol) # Volume total
        self._set_num_item(footer, 0, 7, total_real, sign=True)
        self._set_num_item(footer, 0, 8, total_24h, sign=True)

    def _on_market_header_clicked(self, index):
        """# багана (index 0) дээр дарахад эрэмбэлэхийг идэвхгүй болгох."""
        # Хэрэв 0-р багана биш бол эрэмбэлэлтийг зөвшөөрнө
        self.ui.market_table.setSortingEnabled(index != 0)

    @pyqtSlot(dict)
    def _on_balance_update(self, balance):
        """Балансын мэдээллийг хүлээн авч UI-г шинэчлэх."""
        table = self.ui.balance_table
        sorting_was_enabled = table.isSortingEnabled()
        table.setSortingEnabled(False)
        
        try:
            table.setRowCount(0)
            total_usdt_worth = 0
            
            # CCXT balance-аас койн бүрийн мэдээллийг авах
            # balance['total'] нь нийт, balance['free'] нь арилжаанд бэлэн, balance['used'] нь түгжигдсэн
            for asset, total_val in balance.get('total', {}).items():
                if total_val > 0:
                    row = table.rowCount()
                    table.insertRow(row)
                    
                    free = balance.get('free', {}).get(asset, 0)
                    used = balance.get('used', {}).get(asset, 0)
                    
                    # Баганууд: ["Asset", "Trading", "Exceed", "Funding", "Total(USDT)"]
                    table.setItem(row, 0, QTableWidgetItem(asset))
                    self._set_num_item(table, row, 1, free)    # Trading
                    self._set_num_item(table, row, 2, 0)       # Exceed (Логик орох хэсэг)
                    self._set_num_item(table, row, 3, used)    # Funding
                    self._set_num_item(table, row, 4, total_val) # Total
                    
                    if asset == 'USDT':
                        total_usdt_worth += total_val
            
            # Нийт USDT балансыг label дээр харуулах
            self.ui.total_balance_label.setText(f"Total: ${self._fmt(total_usdt_worth, 2)}")
            
        finally:
            table.setSortingEnabled(sorting_was_enabled)

    @pyqtSlot(dict)
    def _on_net_status_update(self, data):
        """Сүлжээний хяналтын хэсгийг шинэчлэх."""
        if 'latency' in data:
            self.ui.net_latency.setText(f"Latency: {self._fmt(data['latency'], 0)}ms")
        
        self.ui.net_api_status.setText(f"API: {data['rpm']} req/min")
        
        ws_active = data.get('ws_active', False)
        ws_text = "WS: Active" if ws_active else "WS: Inactive"
        self.ui.net_ws_status.setText(ws_text)
        self.ui.net_ws_status.setStyleSheet("color: #10b981;" if ws_active else "color: #ef4444;")

        if data.get('server_time'):
            st = datetime.fromtimestamp(data['server_time'] / 1000).strftime('%H:%M:%S')
            self.ui.net_server_time.setText(f"Server Time: {st}")

    def _ui_heartbeat(self):
        """Таймерын утгуудыг секундээр бууруулж UI дээр харуулах."""
        self.bal_countdown -= 1
        self.sync_countdown -= 1
        self.ui.net_bal_timer.setText(f"BAL: {max(0, self.bal_countdown)}s")
        self.ui.net_sync_timer.setText(f"SYNC: {max(0, self.sync_countdown)}s")
        
        # Railway-аас ирсэн Redis логуудыг шалгах
        self._check_redis_events()

    def _check_redis_events(self):
        """Redis-ээс Railway ботын үйл явдлуудыг унших."""
        if self.kuc.redis:
            try:
                # Сүүлийн ирсэн логийг аваад устгах (pop)
                event_raw = self.kuc.redis.rpop("bot_events")
                if event_raw:
                    event = json.loads(event_raw)
                    self.log_signal.emit(f"🌐 [RAILWAY] {event['msg']}")
            except Exception:
                pass

    def _on_system_heartbeat(self):
        """Системийг бүхэлд нь 1 минут тутамд шинэчлэх."""
        self.sync_countdown = 60 # Таймерыг дахин эхлүүлэх
        self.start_fetch()      # Баланс шинэчлэх
        self.refresh_all()      # Арилжааны түүх шинэчлэх
        self.refresh_profit()   # Ашгийн статистик шинэчлэх

    def _handle_action(self, action_type):
        """Товчлуур дарахад ажиллах ерөнхий функц."""
        symbol = self.ui.selected_symbol_label.text()
        amount = self.ui.amount_input.text()
        # Async тушаал илгээх жишээ
        asyncio.create_task(self.kuc.create_order(symbol, action_type.lower(), float(amount)))
        self.log_signal.emit(f"Order Sent: {action_type} {amount} {symbol}")

    @pyqtSlot()
    def refresh_all(self):
        """UI хүснэгтийг шинэчлэх логик орох хэсэг."""
        pass # Лог дээрх хогийг цэвэрлэв

    @pyqtSlot()
    def refresh_profit(self):
        """Ашгийн түүхийг шинэчлэх логик орох хэсэг."""
        pass # Лог дээрх хогийг цэвэрлэв

    @pyqtSlot()
    def start_fetch(self):
        """Баланс шинэчлэх логик орох хэсэг."""
        self.bal_countdown = 5 # Таймерыг дахин эхлүүлэх
        asyncio.create_task(self.kuc.fetch_balance())

    def get_live_bid(self, symbol):
        return float(self.ws_bids.get(symbol, 0))

    def get_live_ask(self, symbol):
        return float(self.ws_asks.get(symbol, 0))

    def get_live_price(self, symbol):
        """Арилжааны дундаж үнийг (Mid Price) буцаана."""
        bid = self.get_live_bid(symbol)
        ask = self.get_live_ask(symbol)
        return (bid + ask) / 2 if (bid > 0 and ask > 0) else bid or ask

    # --- UI Helper Methods ---

    def _copy_table_to_clipboard(self, table):
        """Хүснэгтийн өгөгдлийг clipboard руу хуулах (Excel-д наахад тохиромжтой)."""
        rows = table.rowCount()
        cols = table.columnCount()
        
        # Header-үүдийг авах
        headers = []
        for c in range(cols):
            header_item = table.horizontalHeaderItem(c)
            headers.append(header_item.text() if header_item else f"Col{c}")
        
        output = ["\t".join(headers)]
        
        # Row-уудыг авах
        for r in range(rows):
            row_data = []
            for c in range(cols):
                item = table.item(r, c)
                row_data.append(item.text() if item else "")
            output.append("\t".join(row_data))
        
        QApplication.clipboard().setText("\n".join(output))
        self.log_signal.emit("Хүснэгтийн өгөгдөл clipboard-д хуулагдлаа.")

    def _copy_history_tab_data(self):
        """History tab-ийн идэвхтэй хүснэгтийг хуулах."""
        index = self.ui.history_tabs.currentIndex()
        table = self.ui.auto_trade_table if index == 0 else self.ui.profit_table
        self._copy_table_to_clipboard(table)

    def _copy_logs(self):
        """Логуудыг clipboard руу хуулах."""
        QApplication.clipboard().setText(self.ui.log_display.toPlainText())
        self.log_signal.emit("Системийн логууд clipboard-д хуулагдлаа.")

    def _update_auto_table(self, data_list):
        self.ui.auto_trade_table.setRowCount(len(data_list))
        for row, data in enumerate(data_list):
            self.ui.auto_trade_table.setItem(row, 0, QTableWidgetItem(str(data.get('pair'))))
            self.ui.auto_trade_table.setItem(row, 1, QTableWidgetItem(str(data.get('time'))))
            self.ui.auto_trade_table.setItem(row, 2, QTableWidgetItem(str(data.get('side'))))
            self.ui.auto_trade_table.setItem(row, 3, QTableWidgetItem(self._fmt(data.get('price', 0))))
            self.ui.auto_trade_table.setItem(row, 4, QTableWidgetItem(self._fmt(data.get('amount', 0))))
            self.ui.auto_trade_table.setItem(row, 6, QTableWidgetItem(str(data.get('status'))))

    def _update_profit_table(self, data_list):
        self.ui.profit_table.setRowCount(len(data_list))
        for row, data in enumerate(data_list):
            self.ui.profit_table.setItem(row, 0, QTableWidgetItem(str(data.get('symbol'))))
            self.ui.profit_table.setItem(row, 4, QTableWidgetItem(self._fmt(data.get('net_profit_usdt', 0))))

    def _load_active_trades(self):
        """Программ эхлэхэд идэвхтэй арилжаануудыг ачаалах."""
        self.active_symbols = {}
        self.log_signal.emit("Skeleton initialized. Ready for logic implementation.")

    @pyqtSlot(str)
    def _append_log_to_ui(self, msg):
        """Лог мессежийг UI дээр цаг хугацаатай харуулах."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.ui.log_display.append(f"[{timestamp}] {msg}")

    def _on_market_select(self, item):
        """Хүснэгтээс зоос сонгоход Ticker label-ийг шинэчлэх."""
        # 1-р багана нь Coin нэр байна
        coin = self.ui.market_table.item(item.row(), 1).text().split(' ')[0]
        self.ui.selected_symbol_label.setText(f"{coin}/USDT")

    def _toggle_strategy(self):
        """Strategy START/STOP логик."""
        strategy_name = self.ui.strategy_combo.currentText()
        if self.ui.start_btn.text() == "START":
            if strategy_name == "Strategy 1":
                self.log_signal.emit("Strategy 1 started")
                self.ui.start_btn.setText("STOP")
                self.ui.start_btn.setStyleSheet(BTN_RED)
        else:
            if strategy_name == "Strategy 1":
                self.log_signal.emit("Strategy 1 stopped")
                self.ui.start_btn.setText("START")
                self.ui.start_btn.setStyleSheet(BTN_ORANGE)

    def _show_mgmt_menu(self):
        """Management товчны доорх цэсийг үүсгэж харуулах."""
        menu = QMenu(self.ui)
        menu.setStyleSheet(MGMT_MENU_STYLE)
        symbol = self.ui.selected_symbol_label.text()
        
        menu.addAction("Sell Exceed Balances", lambda: self.log_signal.emit("Action: Sell Exceed"))
        menu.addAction("Delist Current Ticker", lambda: self.log_signal.emit(f"Action: Delist {symbol}"))
        menu.addSeparator()
        menu.addAction("Clear All Trading", lambda: self.log_signal.emit("Action: Clear All"))
        menu.addAction("Force Sell & Reset All", lambda: self.log_signal.emit("Action: Force Sell"))
        
        menu.exec(self.ui.mgmt_btn.mapToGlobal(self.ui.mgmt_btn.rect().bottomLeft()))

    def _show_hide_menu(self):
        """Маркет хүснэгтийн шүүлтүүрүүдийг харуулах цэс."""
        menu = QMenu(self.ui)
        menu.setStyleSheet(MGMT_MENU_STYLE)
        
        # Цэсний сонголтууд
        menu.addAction("Hide Blacklist", lambda: self.log_signal.emit("Filter: Blacklist active"))
        menu.addAction("Hide Spread", lambda: self.log_signal.emit("Filter: Spread filter active"))
        menu.addAction("Hide Low Vol", lambda: self.log_signal.emit("Filter: Low Vol hidden"))
        menu.addAction("Hide Min High", lambda: self.log_signal.emit("Filter: Min High hidden"))
        menu.addAction("Hide Limit High", lambda: self.log_signal.emit("Filter: Limit High hidden"))
        
        # Товчлуурын доор цэсийг нээх
        menu.exec(self.ui.hide_btn.mapToGlobal(self.ui.hide_btn.rect().bottomLeft()))

    # --- Logic классуудад зориулсан Bridge properties ---
    @property
    def market(self): return self # exchange объект self дотор байгаа тул
    @property
    def history(self): return self # refresh_all, get_live_bid энд байгаа тул
    @property
    def balance(self): return self # start_fetch энд байгаа тул
    @property
    def control(self): return self.ui # amount_input зэргийг уншихад хэрэгтэй