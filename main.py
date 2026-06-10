# Main.py

import sys
import os
import asyncio
import qasync
import traceback
import logging
from PyQt6.QtWidgets import QApplication

# Зам тохируулах
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main_ui import MainTradingUI
from dialog import MainDialog

def global_exception_handler(exctype, value, tb):
    """Unhandled exception-уудыг барьж авах (Sync)"""
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    print(f"CRITICAL ERROR:\n{error_msg}")
    # Энд хэрэв bridge объектод хандаж чадвал UI-руу илгээж болно
    logging.error(error_msg)

def async_exception_handler(loop, context): # type: ignore
    """Async task дотор гарсан алдааг барьж авах"""
    exception = context.get("exception")
    if exception:
        error_msg = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
    else:
        error_msg = context["message"]
    print(f"ASYNC ERROR: {error_msg}")
    logging.error(error_msg)

def main():
    # 1. Программ үүсгэх
    app = QApplication(sys.argv)
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    sys.excepthook = global_exception_handler

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    loop.set_exception_handler(async_exception_handler)
    
    # 2. UI (Template) үүсгэх
    ui = MainTradingUI()
    
    # 3. Логик (Controller) үүсгэж UI-тай холбох
    bridge = MainDialog(ui)
    
    # 4. Программыг харуулах
    ui.show()
    
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()