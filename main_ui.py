# main_ui.py

import sys
import os
# Программ ажиллаж буй хавтсыг хайх замд нэмж өгснөөр style.py-ийг олж чадна
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSplitter, QLabel, QLineEdit, 
                             QComboBox, QPushButton, QFrame, QTabWidget, 
                             QTableWidget, QTextEdit, QHeaderView, QCheckBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

# --- UI Styles ---
PANEL_BG = "background-color: #020617; color: #f8fafc;"
CONTROL_FRAME = """
    QFrame { background-color: #1e293b; border-radius: 8px; border: 1px solid #334155; color: #f8fafc; }
    QLabel { color: #cbd5e1; font-size: 9px; font-weight: bold; border: none; }
"""
NET_PANEL_STYLE = """
    QFrame { background-color: #0f172a; border-radius: 4px; border: 1px solid #1e293b; }
    QLabel { color: #94a3b8; font-size: 10px; font-weight: normal; border: none; }
"""
SYMBOL_LABEL = "color: #fbbf24; font-weight: bold; font-size: 13px;"
INPUT_STYLE = "background: #0f172a; color: white; border: 1px solid #334155; padding-left: 5px;"
COMBO_STYLE = "background: #0f172a; color: white; border: 1px solid #334155;"
STRATEGY_COMBO = "background: #0f172a; color: #38bdf8; border: 1px solid #334155;"
BTN_GREEN = "background-color: #10b981; color: white; font-weight: bold; border-radius: 4px;"
BTN_RED = "background-color: #ef4444; color: white; font-weight: bold; border-radius: 4px;"
BTN_GRAY = "background-color: #475569; color: white; font-weight: bold; border-radius: 4px;"
BTN_ORANGE = "background-color: #f97316; color: white; font-weight: bold; border-radius: 4px;"

TABLE_STYLE = """
    QTableWidget { background-color: #020617; color: #e2e8f0; gridline-color: #1e293b; border: none; }
    QHeaderView::section { background-color: #1e293b; color: #94a3b8; padding: 5px; border: 1px solid #334155; font-weight: bold; }
"""

MGMT_MENU_STYLE = """
    QMenu { background-color: #1e293b; color: white; border: 1px solid #334155; font-size: 12px; }
    QMenu::item { padding: 10px 30px; color: white; background-color: transparent; }
    QMenu::item:selected { background-color: #3b82f6; color: white; }
    QMenu::separator { height: 1px; background: #334155; margin: 5px 0px; }
"""

MARKET_TABLE_STYLE = TABLE_STYLE
HISTORY_TABS_STYLE = """
    QTabWidget::pane { border: 1px solid #1e293b; background: #0f172a; }
    QTabBar::tab { 
        background: #1e293b; color: #94a3b8; padding: 6px 15px; border: 1px solid #334155; 
        border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; 
    }
    QTabBar::tab:selected { background: #0f172a; color: #38bdf8; border-bottom: 2px solid #38bdf8; font-weight: bold; }
    QTabBar::tab:hover { background: #334155; }
"""
HISTORY_TABLE_STYLE = TABLE_STYLE
LOG_DISPLAY_STYLE = """
    background-color: #020617; 
    color: #10b981; 
    font-family: 'Consolas'; 
    font-size: 11px;
    border: 1px solid #1e293b;
"""
# ------------------

class MainTradingUI(QMainWindow):
    """
    Арилжааны терминалын үндсэн UI загвар.
    Бусад файлаас хамааралгүй, бүх элементийг өөртөө агуулсан.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Railway Monolith UI")
        self.resize(1600, 950)
        self.setStyleSheet(PANEL_BG) 

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 1. CONTROL SECTION (Top)
        self.control_panel = self._create_control_section()
        main_layout.addWidget(self.control_panel)

        # 1.5 NETWORK MONITOR SECTION (Thin Panel)
        self.network_panel = self._create_network_section()
        main_layout.addWidget(self.network_panel)

        # 2. MAIN CONTENT - Outer Vertical Splitter (50/50)
        self.main_v_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # --- Top Row: Market (70%) & Balance (30%) ---
        self.top_row_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.top_row_splitter.addWidget(self._create_market_section())
        self.top_row_splitter.addWidget(self._create_balance_section())
        self.top_row_splitter.setStretchFactor(0, 7)
        self.top_row_splitter.setStretchFactor(1, 3)
        self.top_row_splitter.setSizes([1120, 480]) # 1600-ийн 70% ба 30%
        
        # --- Bottom Row: History (70%) & Logs (30%) ---
        self.bottom_row_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.bottom_row_splitter.addWidget(self._create_history_section())
        self.bottom_row_splitter.addWidget(self._create_logs_section())
        self.bottom_row_splitter.setStretchFactor(0, 7)
        self.bottom_row_splitter.setStretchFactor(1, 3)
        self.bottom_row_splitter.setSizes([1120, 480]) # 1600-ийн 70% ба 30%

        self.main_v_splitter.addWidget(self.top_row_splitter)
        self.main_v_splitter.addWidget(self.bottom_row_splitter)
        self.main_v_splitter.setStretchFactor(0, 1)
        self.main_v_splitter.setStretchFactor(1, 1)
        self.main_v_splitter.setSizes([475, 475]) # 950 өндрийн 50/50

        main_layout.addWidget(self.main_v_splitter, 1)

    def _create_control_section(self):
        frame = QFrame()
        frame.setFixedHeight(45)
        frame.setStyleSheet(CONTROL_FRAME)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        # Ticker
        layout.addWidget(QLabel("TICKER:"))
        self.selected_symbol_label = QLabel("BTC/USDT")
        self.selected_symbol_label.setStyleSheet(SYMBOL_LABEL)
        layout.addWidget(self.selected_symbol_label)

        # Market Search (Moved from market section)
        self.market_search = QLineEdit()
        self.market_search.setPlaceholderText("Search...")
        self.market_search.setFixedWidth(120)
        self.market_search.setStyleSheet(INPUT_STYLE)
        layout.addWidget(self.market_search)

        layout.addStretch(1)

        # Amount
        layout.addWidget(QLabel("AMOUNT:"))
        self.amount_input = QLineEdit("0.11")
        self.amount_input.setFixedSize(80, 28)
        self.amount_input.setStyleSheet(INPUT_STYLE)
        layout.addWidget(self.amount_input)

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["USDT", "Coin"])
        self.unit_combo.setFixedSize(70, 28)
        self.unit_combo.setStyleSheet(COMBO_STYLE)
        layout.addWidget(self.unit_combo)

        # Earn Collect
        self.earn_btn = QPushButton("💰 Earn Collect")
        self.earn_btn.setFixedSize(110, 28)
        self.earn_btn.setStyleSheet(BTN_GREEN)
        layout.addWidget(self.earn_btn)
        layout.addStretch(1)

        # Strategy
        layout.addWidget(QLabel("STRATEGY:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["Strategy 1", "Strategy 2"])
        self.strategy_combo.setFixedSize(100, 28)
        self.strategy_combo.setStyleSheet(STRATEGY_COMBO)
        layout.addWidget(self.strategy_combo)

        # Action Buttons
        self.buy_btn = QPushButton("🛒 BUY")
        self.buy_btn.setFixedSize(70, 28)
        self.buy_btn.setStyleSheet(BTN_GREEN)
        layout.addWidget(self.buy_btn)

        self.sell_btn = QPushButton("🔥 SELL")
        self.sell_btn.setFixedSize(70, 28)
        self.sell_btn.setStyleSheet(BTN_RED)
        layout.addWidget(self.sell_btn)

        self.mgmt_btn = QPushButton("⚙️ Management")
        self.mgmt_btn.setFixedSize(100, 28)
        self.mgmt_btn.setStyleSheet(BTN_GRAY)
        layout.addWidget(self.mgmt_btn)

        self.start_btn = QPushButton("START")
        self.start_btn.setFixedSize(70, 28)
        self.start_btn.setStyleSheet(BTN_ORANGE)
        layout.addWidget(self.start_btn)

        return frame

    def _create_network_section(self):
        """Сүлжээний хяналтын нарийн зурвас үүсгэх."""
        frame = QFrame()
        frame.setFixedHeight(22) # Control-оос 2 дахин нимгэн
        frame.setStyleSheet(NET_PANEL_STYLE)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(20)

        # Network Stats Placeholders
        self.net_latency = QLabel("Latency: 0ms")
        self.net_api_status = QLabel("API: Connected")
        self.net_ws_status = QLabel("WS: Active")
        self.net_bal_timer = QLabel("BAL: 5s")
        self.net_sync_timer = QLabel("SYNC: 60s")
        self.net_server_time = QLabel("Server Time: 00:00:00")

        # Стилийн ялгарал өгөх
        self.net_api_status.setStyleSheet("color: #10b981;") # Green
        self.net_ws_status.setStyleSheet("color: #10b981;")  # Green
        self.net_bal_timer.setStyleSheet("color: #fbbf24;")  # Yellow/Gold
        self.net_sync_timer.setStyleSheet("color: #38bdf8;")  # Blue

        layout.addWidget(self.net_latency)
        layout.addWidget(self.net_api_status)
        layout.addWidget(self.net_bal_timer)
        layout.addWidget(self.net_sync_timer)
        layout.addStretch(1) # Зай авах
        layout.addWidget(self.net_server_time)

        # Илүү цэвэрхэн харагдуулахын тулд font хэмжээг жижигсгэх
        return frame

    def _create_market_section(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Controls row
        ctrl_layout = QHBoxLayout()
        self.market_status = QLabel("Kucoin Market: Online")
        self.market_status.setStyleSheet("color: #38bdf8; font-weight: bold;")
        ctrl_layout.addWidget(self.market_status)
        ctrl_layout.addStretch()

        self.market_copy_btn = QPushButton("Copy")
        self.market_copy_btn.setFixedSize(60, 22)
        self.market_copy_btn.setStyleSheet(BTN_GRAY)
        ctrl_layout.addWidget(self.market_copy_btn)

        self.market_max_btn = QPushButton("🔲 Maximize")
        self.market_max_btn.setFixedSize(85, 22)
        self.market_max_btn.setStyleSheet(BTN_GRAY)
        self.market_max_btn.clicked.connect(self.toggle_market_maximize)
        ctrl_layout.addWidget(self.market_max_btn)

        self.hide_btn = QPushButton("👁️ Hide")
        self.hide_btn.setFixedSize(70, 22)
        self.hide_btn.setStyleSheet(BTN_GRAY)
        ctrl_layout.addWidget(self.hide_btn)
        
        layout.addLayout(ctrl_layout)

        # Table
        self.market_table = QTableWidget(0, 10)
        self.market_table.setHorizontalHeaderLabels(["#", "Coin", "Bid", "Ask", "Spread%", "Min $", "Vol", "Real%", "24%", "Limit"])
        self.market_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.market_table.verticalHeader().setVisible(False) # Давхар дугаарлалтыг нуух
        self.market_table.setSortingEnabled(True) # Эрэмбэлэлтийг идэвхжүүлэх
        self.market_table.setStyleSheet(MARKET_TABLE_STYLE)
        layout.addWidget(self.market_table)

        # Market Total Table (Fixed Footer)
        self.market_total_table = QTableWidget(1, 10)
        self.market_total_table.setFixedHeight(25)
        self.market_total_table.horizontalHeader().setVisible(False)
        self.market_total_table.verticalHeader().setVisible(False)
        self.market_total_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.market_total_table.setStyleSheet(MARKET_TABLE_STYLE + "QTableWidget { background-color: #1e293b; font-weight: bold; }")
        self.market_total_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.market_total_table)

        return widget

    def _create_history_section(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.history_tabs = QTabWidget()
        self.history_tabs.setStyleSheet(HISTORY_TABS_STYLE)

        # Auto Trades Table
        auto_container = QWidget()
        auto_layout = QVBoxLayout(auto_container)
        auto_layout.setContentsMargins(0,0,0,0)
        auto_layout.setSpacing(0)

        self.auto_trade_table = QTableWidget(0, 7)
        self.auto_trade_table.setHorizontalHeaderLabels(["Pair", "Time", "Side", "Price", "Amount", "Live %", "Status"])
        self.auto_trade_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.auto_trade_table.verticalHeader().setVisible(False)
        self.auto_trade_table.setStyleSheet(HISTORY_TABLE_STYLE)
        auto_layout.addWidget(self.auto_trade_table)

        self.auto_total_table = QTableWidget(1, 7)
        self.auto_total_table.setFixedHeight(25)
        self.auto_total_table.horizontalHeader().setVisible(False)
        self.auto_total_table.verticalHeader().setVisible(False)
        self.auto_total_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.auto_total_table.setStyleSheet(HISTORY_TABLE_STYLE + "QTableWidget { background-color: #1e293b; }")
        auto_layout.addWidget(self.auto_total_table)

        # Profit Summary Table
        profit_container = QWidget()
        profit_layout = QVBoxLayout(profit_container)
        profit_layout.setContentsMargins(0,0,0,0)
        profit_layout.setSpacing(0)

        self.profit_table = QTableWidget(0, 6)
        self.profit_table.setHorizontalHeaderLabels(["Pair", "Sell Time", "Buy Price", "Sell Price", "Profit USDT", "Profit %"])
        self.profit_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.profit_table.verticalHeader().setVisible(False)
        self.profit_table.setStyleSheet(HISTORY_TABLE_STYLE)
        profit_layout.addWidget(self.profit_table)

        self.profit_total_table = QTableWidget(1, 6)
        self.profit_total_table.setFixedHeight(25)
        self.profit_total_table.horizontalHeader().setVisible(False)
        self.profit_total_table.verticalHeader().setVisible(False)
        self.profit_total_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.profit_total_table.setStyleSheet(HISTORY_TABLE_STYLE + "QTableWidget { background-color: #1e293b; }")
        profit_layout.addWidget(self.profit_total_table)

        self.history_tabs.addTab(auto_container, "Auto Trades")
        self.history_tabs.addTab(profit_container, "Profit Summary")

        # Corner buttons for History
        corner_widget = QWidget()
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(0, 0, 5, 0)
        self.history_copy_btn = QPushButton("Copy")
        self.history_copy_btn.setFixedSize(60, 20)
        self.history_copy_btn.setStyleSheet(BTN_GRAY)
        corner_layout.addWidget(self.history_copy_btn)

        self.history_max_btn = QPushButton("🔲 Maximize")
        self.history_max_btn.setFixedSize(85, 20)
        self.history_max_btn.setStyleSheet(BTN_GRAY)
        self.history_max_btn.clicked.connect(self.toggle_history_maximize)
        corner_layout.addWidget(self.history_max_btn)

        self.history_tabs.setCornerWidget(corner_widget, Qt.Corner.TopRightCorner)

        layout.addWidget(self.history_tabs)
        return widget

    def _create_balance_section(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        top_bar = QHBoxLayout()
        self.balance_status = QLabel("Wallet: Live")
        self.balance_status.setStyleSheet("color: #10b981; font-weight: bold;")
        top_bar.addWidget(self.balance_status)
        top_bar.addStretch()

        self.balance_copy_btn = QPushButton("Copy")
        self.balance_copy_btn.setFixedSize(60, 20)
        self.balance_copy_btn.setStyleSheet(BTN_GRAY)
        top_bar.addWidget(self.balance_copy_btn)
        
        self.total_balance_label = QLabel("Total: $0.00")
        self.total_balance_label.setStyleSheet("color: #fbbf24; font-weight: bold; font-size: 12px;")
        top_bar.addWidget(self.total_balance_label)
        layout.addLayout(top_bar)

        self.balance_table = QTableWidget(0, 5)
        self.balance_table.setHorizontalHeaderLabels(["Asset", "Trading", "Exceed", "Funding", "Total(USDT)"])
        self.balance_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.balance_table.verticalHeader().setVisible(False)
        self.balance_table.setStyleSheet("background-color: #0f172a; color: white; border: none;")
        layout.addWidget(self.balance_table)

        # Balance Total Table (Fixed Footer)
        self.balance_total_table = QTableWidget(1, 5)
        self.balance_total_table.setFixedHeight(25)
        self.balance_total_table.horizontalHeader().setVisible(False)
        self.balance_total_table.verticalHeader().setVisible(False)
        self.balance_total_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.balance_total_table.setStyleSheet("background-color: #1e293b; color: #fbbf24; border: none; font-weight: bold;")
        layout.addWidget(self.balance_total_table)

        return widget

    def _create_logs_section(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.addWidget(QLabel("SYSTEM LOGS"))
        header.addStretch()
        self.logs_copy_btn = QPushButton("Copy")
        self.logs_copy_btn.setFixedSize(60, 22)
        self.logs_copy_btn.setStyleSheet(BTN_GRAY)
        header.addWidget(self.logs_copy_btn)
        layout.addLayout(header)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("""
            background-color: #020617; 
            color: #10b981; 
            font-family: 'Consolas'; 
            font-size: 11px;
            border: 1px solid #1e293b;
        """)
        layout.addWidget(self.log_display)

        return widget

    def toggle_market_maximize(self):
        if self.bottom_row_splitter.isVisible():
            self.bottom_row_splitter.hide()
            self.market_max_btn.setText("🔳 Restore")
        else:
            self.bottom_row_splitter.show()
            self.market_max_btn.setText("🔲 Maximize")

    def toggle_history_maximize(self):
        if self.top_row_splitter.isVisible():
            self.top_row_splitter.hide()
            self.history_max_btn.setText("🔳 Restore")
        else:
            self.top_row_splitter.show()
            self.history_max_btn.setText("🔲 Maximize")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = MainTradingUI()
    ui.show()
    sys.exit(app.exec())