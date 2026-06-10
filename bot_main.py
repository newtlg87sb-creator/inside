import asyncio
import os
from engine.kuc_client import KucoinClient

async def main():
    print("Бот ажиллаж эхэллээ (Headless Mode)...")
    
    # 1. Клиент эхлүүлэх
    client = KucoinClient()
    
    # 2. Сигналуудын оронд консол дээр лог хэвлэх (Optional)
    client.price_signal.connect(lambda data: print(f"Price Update: {data['symbol']} -> {data['bid']}"))
    client.error_signal.connect(lambda msg: print(f"!!! ERROR: {msg}"))
    
    # 3. WebSocket урсгалыг эхлүүлэх
    client.start_market_stream()
    
    # 4. Баланс тогтмол шалгах логик (Жишээ)
    while True:
        await client.fetch_balance()
        await asyncio.sleep(60) # 1 минут тутамд

if __name__ == "__main__":
    try:
        # Railway дээр asyncio loop-ийг шууд ажиллуулна
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот зогслоо.")
    except Exception as e:
        print(f"Гэнэтийн алдаа: {e}")