#!/usr/bin/env python3
"""
Тестовый файл для проверки основных функций Telegram Stars Bot
"""

import asyncio
import sys
import os
from datetime import datetime

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import OrderStatus, FulfillmentStatus
from database import db
from integrations import funpay, fragment, utils
from message_templates import MessageTemplates

async def test_database():
    """Тест базы данных"""
    print("🧪 Тестирование базы данных...")
    
    # Тест создания заказа
    test_order = {
        'order_id': 'test_order_001',
        'offer_id': 'offer_1',
        'quantity': 2,
        'buyer_username': 'test_user',
        'buyer_funpay_login': 'test_funpay',
        'total_price': 200.0,
        'currency': 'RUB',
        'status': OrderStatus.NEW,
        'attached_telegram_username': '@testuser',
        'created_at': utils.now(),
        'stars_amount_total': 200
    }
    
    db.save_order(test_order)
    print("✅ Заказ сохранён в БД")
    
    # Тест получения заказа
    retrieved_order = db.get_order('test_order_001')
    if retrieved_order:
        print(f"✅ Заказ получен: {retrieved_order['order_id']}")
    else:
        print("❌ Ошибка получения заказа")
    
    # Тест создания fulfillment
    fulfillment_record = {
        'order_id': 'test_order_001',
        'to_username': '@testuser',
        'stars_total': 200,
        'batches': [
            {'amount': 200, 'transfer_id': 'tr_test_001', 'status': 'ok'}
        ],
        'status': FulfillmentStatus.SUCCESS,
        'created_at': utils.now(),
        'updated_at': utils.now(),
        'notes': 'test fulfillment'
    }
    
    fulfillment_id = db.create_fulfillment(fulfillment_record)
    print(f"✅ Fulfillment создан: {fulfillment_id}")
    
    # Тест получения fulfillment
    fulfillment = db.get_fulfillment_by_order('test_order_001')
    if fulfillment:
        print(f"✅ Fulfillment получен: {fulfillment['status']}")
    else:
        print("❌ Ошибка получения fulfillment")

async def test_integrations():
    """Тест интеграций"""
    print("\n🧪 Тестирование интеграций...")
    
    # Тест FunPay
    try:
        offers = await funpay.list_offers()
        print(f"✅ FunPay offers получены: {len(offers)} офферов")
        
        order_data = await funpay.get_order('test_order_001')
        print(f"✅ FunPay order получен: {order_data['order_id']}")
        
        payment_status = await funpay.verify_payment('test_order_001')
        print(f"✅ FunPay payment проверен: {payment_status['paid']}")
        
    except Exception as e:
        print(f"❌ Ошибка FunPay: {e}")
    
    # Тест Fragment
    try:
        balance = await fragment.get_balance()
        print(f"✅ Fragment balance получен: {balance['stars_balance']} ⭐")
        
        transfer_result = await fragment.transfer_stars(
            '@testuser', 
            100, 
            utils.generate_idempotency_key('test_order_001', '@testuser', 100)
        )
        print(f"✅ Fragment transfer: {transfer_result['ok']}")
        
    except Exception as e:
        print(f"❌ Ошибка Fragment: {e}")

async def test_utils():
    """Тест утилит"""
    print("\n🧪 Тестирование утилит...")
    
    # Тест валидации юзернейма
    test_usernames = [
        'testuser',      # ✅
        '@testuser',     # ✅
        'test',          # ❌ (слишком короткий)
        'test@user',     # ❌ (неверные символы)
        'a' * 33,        # ❌ (слишком длинный)
    ]
    
    for username in test_usernames:
        is_valid = utils.validate_username(username)
        status = "✅" if is_valid else "❌"
        print(f"{status} {username}: {is_valid}")
    
    # Тест нормализации юзернейма
    normalized = utils.normalize_username('testuser')
    print(f"✅ Нормализация: testuser → {normalized}")
    
    # Тест разбивки на батчи
    batches = utils.split_stars_into_batches(25000, 20000)
    print(f"✅ Разбивка 25000 на батчи: {batches}")
    
    # Тест маскирования ID
    masked = utils.mask_transaction_id('tx_1234567890abcdef')
    print(f"✅ Маскирование ID: {masked}")
    
    # Тест генерации idempotency key
    key = utils.generate_idempotency_key('order_001', '@user', 100)
    print(f"✅ Idempotency key: {key[:20]}...")

async def test_message_templates():
    """Тест шаблонов сообщений"""
    print("\n🧪 Тестирование шаблонов сообщений...")
    
    templates = MessageTemplates()
    
    # Тест приветственного сообщения
    start_msg = templates.start_message()
    print(f"✅ Start message: {len(start_msg)} символов")
    
    # Тест сообщения о ценах
    test_offers = [
        {
            'offer_id': 'offer_1',
            'title': '100 Telegram Stars',
            'stars_amount': 100,
            'price': 100.0,
            'currency': 'RUB',
            'is_active': True
        }
    ]
    price_msg = templates.price_message(test_offers)
    print(f"✅ Price message: {len(price_msg)} символов")
    
    # Тест сообщения о статусе заказа
    test_order = {
        'order_id': 'test_order_001',
        'status': OrderStatus.FULFILLED,
        'stars_amount_total': 200,
        'total_price': 200.0,
        'currency': 'RUB',
        'created_at': utils.now(),
        'attached_telegram_username': '@testuser'
    }
    status_msg = templates.order_status(test_order)
    print(f"✅ Status message: {len(status_msg)} символов")

async def test_order_processor():
    """Тест обработчика заказов"""
    print("\n🧪 Тестирование обработчика заказов...")
    
    # Создаём мок notification service
    class MockNotificationService:
        async def notify_user(self, chat_id, message):
            print(f"📱 Уведомление пользователю {chat_id}: {message[:50]}...")
        
        async def notify_admin(self, message):
            print(f"👨‍💼 Уведомление админу: {message[:50]}...")
    
    from order_processor import OrderProcessor
    processor = OrderProcessor(MockNotificationService())
    
    # Тест обработки заказа
    try:
        await processor.process_order('test_order_001', 123456789)
        print("✅ Обработка заказа завершена")
    except Exception as e:
        print(f"❌ Ошибка обработки заказа: {e}")

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов Telegram Stars Bot\n")
    
    try:
        await test_database()
        await test_integrations()
        await test_utils()
        await test_message_templates()
        await test_order_processor()
        
        print("\n🎉 Все тесты завершены успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Проверяем наличие .env файла
    if not os.path.exists('.env'):
        print("⚠️  Файл .env не найден. Создайте его на основе env_example.txt")
        print("Для тестирования будут использованы мок-данные.")
    
    asyncio.run(main())
