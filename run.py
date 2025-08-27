#!/usr/bin/env python3
"""
Скрипт для запуска Telegram Stars Bot
"""

import asyncio
import sys
import os
from pathlib import Path

def check_requirements():
    """Проверка требований для запуска"""
    print("🔍 Проверка требований...")
    
    # Проверка Python версии
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        return False
    
    # Проверка .env файла
    if not os.path.exists('.env'):
        print("⚠️  Файл .env не найден")
        print("📝 Создайте .env на основе env_example.txt")
        return False
    
    # Проверка зависимостей
    try:
        import telegram
        import aiohttp
        import dotenv
        print("✅ Все зависимости установлены")
        return True
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("📦 Установите зависимости: pip install -r requirements.txt")
        return False

async def main():
    """Основная функция запуска"""
    print("🚀 Запуск Telegram Stars Bot")
    print("=" * 50)
    
    # Проверка требований
    if not check_requirements():
        sys.exit(1)
    
    try:
        # Импорт после проверки зависимостей
        from bot import main as bot_main
        
        print("✅ Все проверки пройдены")
        print("🤖 Запуск бота...")
        
        # Запуск бота
        await bot_main()
        
    except KeyboardInterrupt:
        print("\n⏹️  Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка запуска бота: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Установка кодировки для корректного отображения
    if sys.platform.startswith('win'):
        import locale
        locale.setlocale(locale.LC_ALL, '')
    
    asyncio.run(main())
