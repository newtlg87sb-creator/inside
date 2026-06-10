import asyncio
import os
from engine.kuc_client import KucoinClient

async def main():
    print("Бот ажиллаж эхэллээ (Headless Mode)...")
    
    # 1. Клиент эхлүүлэх
    client = KucoinClient()
    
    # 2. Сигналуудын оронд консол дээр лог хэвлэх (Optional)
    client.error_signal.connect(lambda msg: client.log_event(msg, "ERROR"))
    
    # 3. WebSocket урсгалыг эхлүүлэх
    client.start_market_stream()
    client.log_event("WebSocket урсгал эхэллээ.", "INFO")
    
    # 4. Хяналтын гогцоо (Баланс шалгах + Ажиллаж байгааг мэдэгдэх)
    while True:
        await client.fetch_balance()
        client.log_event("Бот хэвийн ажиллаж байна. Баланс шинэчлэгдлээ.", "INFO")
        await asyncio.sleep(60) # 1 минут тутамд

if __name__ == "__main__":
    try:
        # Railway дээр asyncio loop-ийг шууд ажиллуулна
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот зогслоо.")
    except Exception as e:
        print(f"Гэнэтийн алдаа: {e}")