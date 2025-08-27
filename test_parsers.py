#!/usr/bin/env python3
"""
Тест парсеров FunPay и Fragment
"""

import asyncio
import sys
import os
from datetime import datetime

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from funpay_parser import FunPayParser, MockFunPayParser
from fragment_parser import FragmentParser, MockFragmentParser
from integrations import FunPayAPI, FragmentAPI

class MockNotificationService:
    async def notify_user(self, chat_id, message):
        print(f"📱 Уведомление пользователю {chat_id}: {message[:50]}...")
    
    async def notify_admin(self, message):
        print(f"👨‍💼 Уведомление админу: {message[:100]}...")

async def test_funpay_parser():
    """Тест парсера FunPay"""
    print("🧪 Тестирование FunPay парсера...")
    
    # Создание mock парсера
    parser = MockFunPayParser("test_login", "test_password")
    
    # Тест авторизации
    login_result = await parser.login()
    print(f"✅ Авторизация: {login_result}")
    
    # Тест получения заказов
    orders = await parser.get_orders()
    print(f"✅ Получено заказов: {len(orders)}")
    
    if orders:
        order = orders[0]
        print(f"   📋 Заказ: {order['order_id']}")
        print(f"   ⭐ Звёзды: {order['stars_amount_total']}")
        print(f"   💰 Цена: {order['total_price']} {order['currency']}")
        print(f"   👤 Покупатель: {order['buyer_username']}")
        print(f"   📱 Telegram: {order['attached_telegram_username']}")
    
    # Тест получения деталей заказа
    if orders:
        order_details = await parser.get_order_details(orders[0]['order_id'])
        print(f"✅ Детали заказа: {order_details}")
    
    # Тест проверки оплаты
    payment_status = await parser.verify_payment("test_order_123")
    print(f"✅ Статус оплаты: {payment_status}")
    
    # Тест отправки сообщения
    message_result = await parser.send_message("test_order_123", "Тестовое сообщение")
    print(f"✅ Отправка сообщения: {message_result}")
    
    # Очистка
    parser.close()

async def test_fragment_parser():
    """Тест парсера Fragment"""
    print("\n🧪 Тестирование Fragment парсера...")
    
    # Создание mock парсера
    parser = MockFragmentParser("+1234567890")
    
    # Тест авторизации
    login_result = await parser.login()
    print(f"✅ Авторизация: {login_result}")
    
    # Тест получения баланса
    balance = await parser.get_balance()
    print(f"✅ Баланс: {balance['stars_balance']:,} ⭐")
    print(f"   📊 Дневной лимит: {balance['daily_limit_left']:,}")
    
    # Тест отправки Stars
    transfer_result = await parser.transfer_stars(
        "@testuser", 
        100, 
        "test_key_123"
    )
    print(f"✅ Отправка Stars: {transfer_result}")
    
    # Очистка
    parser.close()

async def test_integrations():
    """Тест интеграций с парсерами"""
    print("\n🧪 Тестирование интеграций...")
    
    # Создание notification service
    notification_service = MockNotificationService()
    
    # Тест FunPay API
    funpay_api = FunPayAPI()
    
    # Получение офферов
    offers = await funpay_api.list_offers()
    print(f"✅ FunPay офферы: {len(offers)}")
    
    for offer in offers:
        print(f"   📦 {offer['title']}: {offer['price']} {offer['currency']}")
    
    # Получение заказа
    order = await funpay_api.get_order("test_order_123")
    print(f"✅ FunPay заказ: {order['order_id']}")
    
    # Проверка оплаты
    payment = await funpay_api.verify_payment("test_order_123")
    print(f"✅ FunPay оплата: {payment['paid']}")
    
    # Тест Fragment API
    fragment_api = FragmentAPI()
    
    # Получение баланса
    balance = await fragment_api.get_balance()
    print(f"✅ Fragment баланс: {balance['stars_balance']:,} ⭐")
    
    # Отправка Stars
    transfer = await fragment_api.transfer_stars(
        "@testuser", 
        100, 
        "test_transfer_key"
    )
    print(f"✅ Fragment отправка: {transfer['ok']}")
    
    if transfer['ok']:
        print(f"   🆔 Transfer ID: {transfer['transfer_id']}")

async def test_parser_workflow():
    """Тест полного workflow с парсерами"""
    print("\n🧪 Тестирование полного workflow...")
    
    # Создание API объектов
    funpay_api = FunPayAPI()
    fragment_api = FragmentAPI()
    
    # Симуляция обработки заказа
    print("📋 Симуляция обработки заказа...")
    
    # 1. Получение заказов
    orders = await funpay_api.list_offers()
    if not orders:
        print("❌ Нет доступных заказов")
        return
    
    # 2. Получение деталей первого заказа
    order_id = "test_order_workflow"
    order_details = await funpay_api.get_order(order_id)
    print(f"📋 Заказ {order_id}: {order_details['stars_amount_total']} ⭐")
    
    # 3. Проверка оплаты
    payment_status = await funpay_api.verify_payment(order_id)
    if payment_status['paid']:
        print("✅ Заказ оплачен")
        
        # 4. Проверка баланса Fragment
        balance = await fragment_api.get_balance()
        stars_needed = order_details['stars_amount_total']
        
        if balance['stars_balance'] >= stars_needed:
            print(f"✅ Достаточно баланса: {balance['stars_balance']:,} ⭐")
            
            # 5. Отправка Stars
            telegram_username = order_details.get('attached_telegram_username', '@testuser')
            transfer_result = await fragment_api.transfer_stars(
                telegram_username,
                stars_needed,
                f"workflow_{order_id}"
            )
            
            if transfer_result['ok']:
                print(f"✅ Stars отправлены! ID: {transfer_result['transfer_id']}")
            else:
                print(f"❌ Ошибка отправки: {transfer_result['error_message']}")
        else:
            print(f"❌ Недостаточно баланса: нужно {stars_needed}, есть {balance['stars_balance']}")
    else:
        print("❌ Заказ не оплачен")

async def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование парсеров FunPay и Fragment\n")
    
    try:
        await test_funpay_parser()
        await test_fragment_parser()
        await test_integrations()
        await test_parser_workflow()
        
        print("\n🎉 Все тесты парсеров завершены успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах парсеров: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Проверяем наличие .env файла
    if not os.path.exists('.env'):
        print("⚠️  Файл .env не найден. Создайте его на основе env_example.txt")
        print("Для тестирования будут использованы mock парсеры.")
    
    asyncio.run(main())
