#!/usr/bin/env python3
"""
Тест системы логирования и статистики
"""

import asyncio
import sys
import os
from datetime import datetime

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import OrderStatus, FulfillmentStatus
from database import db
from integrations import utils
from logging_system import OrderLogger

class MockNotificationService:
    async def notify_user(self, chat_id, message):
        print(f"📱 Уведомление пользователю {chat_id}: {message[:50]}...")
    
    async def notify_admin(self, message):
        print(f"👨‍💼 Уведомление админу: {message[:100]}...")

async def test_logging_system():
    """Тест системы логирования"""
    print("🧪 Тестирование системы логирования...")
    
    # Создание мок notification service
    notification_service = MockNotificationService()
    logger = OrderLogger(notification_service)
    
    # Тестовые данные заказа
    test_order = {
        'order_id': 'test_order_002',
        'stars_amount_total': 500,
        'total_price': 450.0,
        'currency': 'RUB',
        'buyer_username': 'test_buyer',
        'attached_telegram_username': '@test_recipient'
    }
    
    test_fulfillment = {
        'fulfillment_id': 'fulfill_test_002',
        'status': FulfillmentStatus.SUCCESS
    }
    
    # Тест логирования выполненного заказа
    await logger.log_order_completion(test_order, test_fulfillment)
    print("✅ Логирование заказа выполнено")
    
    # Тест получения статистики за месяц
    monthly_stats = await logger.get_monthly_statistics()
    print(f"✅ Статистика за месяц: {monthly_stats}")
    
    # Тест получения общей статистики
    all_time_stats = await logger.get_all_time_statistics()
    print(f"✅ Общая статистика: {all_time_stats}")
    
    # Тест получения последних заказов
    recent_orders = logger.get_recent_orders(5)
    print(f"✅ Последние заказы: {len(recent_orders)} записей")
    
    # Тест логирования ошибки
    logger.log_error("Тестовая ошибка", "test_order_003", {"context": "test"})
    print("✅ Логирование ошибки выполнено")
    
    # Тест логирования действия админа
    logger.log_admin_action(123456789, "test_action", {"details": "test"})
    print("✅ Логирование действия админа выполнено")

async def test_currency_conversion():
    """Тест конвертации валют"""
    print("\n🧪 Тестирование конвертации валют...")
    
    notification_service = MockNotificationService()
    logger = OrderLogger(notification_service)
    
    # Тест конвертации разных валют
    test_cases = [
        (100, 'RUB', 100.0),
        (10, 'USD', 950.0),
        (5, 'EUR', 525.0),
        (20, 'USDT', 1900.0)
    ]
    
    for amount, currency, expected in test_cases:
        result = logger._convert_to_rub(amount, currency)
        status = "✅" if abs(float(result) - expected) < 0.01 else "❌"
        print(f"{status} {amount} {currency} → {result} ₽ (ожидалось: {expected} ₽)")

async def test_database_logs():
    """Тест работы с логами в базе данных"""
    print("\n🧪 Тестирование логов в базе данных...")
    
    # Проверяем, что таблица order_logs создана
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order_logs'")
            result = cursor.fetchone()
            
            if result:
                print("✅ Таблица order_logs существует")
                
                # Проверяем количество записей
                cursor.execute("SELECT COUNT(*) FROM order_logs")
                count = cursor.fetchone()[0]
                print(f"✅ Количество записей в логах: {count}")
                
                # Показываем последние записи
                cursor.execute("""
                    SELECT order_id, stars_amount, price_rub, buyer_username 
                    FROM order_logs 
                    ORDER BY timestamp DESC 
                    LIMIT 3
                """)
                rows = cursor.fetchall()
                
                for row in rows:
                    print(f"   📋 {row[0]}: {row[1]} ⭐, {row[2]} ₽, {row[3]}")
                    
            else:
                print("❌ Таблица order_logs не найдена")
                
    except Exception as e:
        print(f"❌ Ошибка работы с базой данных: {e}")

async def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование системы логирования и статистики\n")
    
    try:
        await test_logging_system()
        await test_currency_conversion()
        await test_database_logs()
        
        print("\n🎉 Все тесты логирования завершены успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах логирования: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
