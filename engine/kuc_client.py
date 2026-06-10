import ccxt.pro as ccxt
import asyncio
import os
import traceback
import time
import json

class Signal:
    """A simple signal class to replace pyqtSignal for headless environments."""
    def __init__(self):
        self._slots = []
    def connect(self, slot):
        self._slots.append(slot)
    def emit(self, *args, **kwargs):
        for slot in self._slots:
            slot(*args, **kwargs)

class KucoinClient:
    """
    KuCoin API болон WebSocket (ccxt.pro) мэдээллийн урсгалыг async хэлбэрээр хариуцах класс.
    """

    def __init__(self):
        self.price_signal = Signal()
        self.balance_signal = Signal()
        self.error_signal = Signal()
        self.net_status_signal = Signal()
        self.exchange = ccxt.kucoin({
            'apiKey': os.getenv('KUCOIN_API_KEY', ''),
            'secret': os.getenv('KUCOIN_SECRET', ''),
            'password': os.getenv('KUCOIN_PASSWORD', ''),
            'enableRateLimit': True,
        })
        self.is_streaming = False
        self.markets_info = {} # Initialize markets_info here
        self.req_history = [] # Requests timestamps for RPM calculation

    def _track_request(self):
        """Хүсэлт бүрийг тэмдэглэж RPM тооцоход ашиглана."""
        now = time.time()
        self.req_history.append(now)
        # 60 секундээс хуучин түүхийг устгах
        self.req_history = [t for t in self.req_history if t > now - 60]

    async def fetch_balance(self):
        """Нийт балансын мэдээллийг татаж авах."""
        try:
            start_time = time.perf_counter()
            balance = await self.exchange.fetch_balance()
            self._track_request()
            self._emit_net_status(start_time)
            self.balance_signal.emit(balance)
            return balance
        except Exception as e:
            full_error = traceback.format_exc()
            self.error_signal.emit(f"Balance Fetch Error:\n{full_error}")
            return None

    def start_market_stream(self):
        """
        WebSocket урсгалыг async task болгон эхлүүлэх.
        """
        if self.is_streaming:
            return

        self.is_streaming = True
        asyncio.get_event_loop().create_task(self._run_stream())
        asyncio.get_event_loop().create_task(self._network_monitor_loop())

    async def _network_monitor_loop(self):
        """Сүлжээний хоцролт болон төлөвийг 3 секунд тутамд шалгах."""
        while self.is_streaming:
            try:
                start_time = time.perf_counter()
                # Серверийн цагийг авах замаар RTT (Latency) хэмжих
                await self.exchange.fetch_time()
                self._track_request()
                self._emit_net_status(start_time)
            except Exception:
                # Алдаа гарвал WS төлөвийг индикатор болгож харуулна
                self.net_status_signal.emit({
                    'latency': 0,
                    'rpm': len(self.req_history),
                    'ws_active': self.is_streaming,
                    'server_time': self.exchange.milliseconds()
                })
            await asyncio.sleep(3) # 3 секундын давтамж

    async def _run_stream(self):
        """watch_tickers ашиглан бодит хугацааны үнийг хүлээн авах."""
        # 1. Эхлээд топ 50 USDT хослолыг эзэлхүүнээр нь шүүж авах
        try:
            start_time = time.perf_counter()
            cache_file = "market_cache.json"
            now = time.time()
            needs_update = True

            # 24 цагийн кэш шалгах
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                    
                    last_update = cache_data.get("_updated_at", 0)
                    if now - last_update < 86400: # 86400 сек = 24 цаг
                        self.markets_info = {
                            sym: {'min_amount': val[0], 'min_cost': val[1]}
                            for sym, val in cache_data.items() if sym != "_updated_at"
                        }
                        needs_update = False
                except Exception:
                    needs_update = True

            if needs_update:
                markets = await self.exchange.load_markets()
                save_data = {"_updated_at": now}
                for market_id, m in markets.items():
                    sym = m['symbol']
                    min_cost = m['limits']['cost']['min'] if m['limits']['cost'] and m['limits']['cost']['min'] is not None else 0.0
                    min_amount = m['limits']['amount']['min'] if m['limits']['amount'] and m['limits']['amount']['min'] is not None else 0.0
                    
                    self.markets_info[sym] = {
                        'min_cost': min_cost,
                        'min_amount': min_amount,
                    }
                    save_data[sym] = [min_amount, min_cost, False]
                
                with open(cache_file, 'w') as f:
                    json.dump(save_data, f)

            all_tickers = await self.exchange.fetch_tickers()
            self._track_request()
            self._emit_net_status(start_time)

            # Leveraged tokens (3L, 3S) болон USDT бус хослолуудыг хасна
            usdt_pairs = [s for s, t in all_tickers.items() if s.endswith('/USDT') and '3L' not in s and '3S' not in s]
            symbols = set(usdt_pairs) # Бүх USDT хослолыг хянах
            
            # Эхний өгөгдлүүдийг UI-руу шууд илгээх
            for sym_name in usdt_pairs:
                ticker_data = all_tickers[sym_name]
                market_limits = self.markets_info.get(sym_name, {})
                merged_data = {**ticker_data, **market_limits}
                self._emit_ticker(merged_data)

        except Exception as e:
            full_error = traceback.format_exc()
            self.error_signal.emit(f"Initial Ticker Fetch Error:\n{full_error}")
            symbols = ['BTC/USDT', 'ETH/USDT']

        while self.is_streaming:
            try:
                # watch_tickers-ийг аргументгүй дуудвал KuCoin-ийн 'all' ticker урсгалыг ашиглана.
                # Энэ нь WebSocket-ийн хязгаарлалтад (subscription limit) орохгүй хамгийн найдвартай арга.
                updates = await self.exchange.watch_tickers()
                self.net_status_signal.emit({
                    'ws_active': True,
                    'server_time': self.exchange.milliseconds(),
                    'rpm': len(self.req_history)
                })
                for sym_name, ticker_data in updates.items():
                    if sym_name in symbols:
                        market_limits = self.markets_info.get(sym_name, {})
                        merged_data = {**ticker_data, **market_limits}
                        self._emit_ticker(merged_data)
                        
            except Exception as e:
                full_error = traceback.format_exc()
                self.error_signal.emit(f"WebSocket Error:\n{full_error}")
                await asyncio.sleep(5)  # Алдаа гарвал 5 сек хүлээгээд дахин холбогдоно

    def _emit_ticker(self, t):
        """Ticker өгөгдлийг стандарт хэлбэрт оруулж сигнал илгээх."""
        # Зөвхөн арилжаанд хэрэгтэй ask, bid болон статистик мэдээллийг илгээнэ
        bid_price = t.get('bid') if t.get('bid') is not None else 0.0
        ask_price = t.get('ask') if t.get('ask') is not None else 0.0
        percentage_change = t.get('percentage') # 24h change, can be None
        quote_volume = t.get('quoteVolume') if t.get('quoteVolume') is not None else 0.0

        self.price_signal.emit({
            'symbol': t.get('symbol'),
            'bid': bid_price,
            'ask': ask_price,
            'change': percentage_change,
            'volume': quote_volume,
            'min_cost': t.get('min_cost', 0.0), # Added min_cost
            'min_amount': t.get('min_amount', 0.0) # Added min_amount
        })

    def _emit_net_status(self, start_time):
        """Сүлжээний төлөв байдлыг мэдээлэх."""
        latency = (time.perf_counter() - start_time) * 1000
        self.net_status_signal.emit({
            'latency': latency,
            'rpm': len(self.req_history),
            'server_time': self.exchange.milliseconds(),
            'ws_active': self.is_streaming
        })

    async def stop_stream(self):
        """Урсгалыг зогсоох."""
        self.is_streaming = False
        await self.exchange.close()

    async def create_order(self, symbol, side, amount, order_type='market', price=None):
        """Арилжааны тушаал илгээх."""
        try:
            start_time = time.perf_counter()
            if order_type == 'market':
                res = await self.exchange.create_market_order(symbol, side, amount)
            else:
                res = await self.exchange.create_limit_order(symbol, side, amount, price)
            self._track_request()
            self._emit_net_status(start_time)
            return res
        except Exception as e:
            full_error = traceback.format_exc()
            self.error_signal.emit(f"Order Execution Error:\n{full_error}")
            return None