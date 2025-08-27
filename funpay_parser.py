"""
Парсер FunPay для автоматического получения заказов
"""

import time
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import requests
import re

class FunPayParser:
    def __init__(self, login: str, password: str, headless: bool = True):
        self.login = login
        self.password = password
        self.headless = headless
        self.driver = None
        self.session = requests.Session()
        self.is_logged_in = False
        
        # Селекторы для элементов страницы
        self.selectors = {
            'login_form': 'form[action="/account/login/"]',
            'login_input': 'input[name="login"]',
            'password_input': 'input[name="password"]',
            'login_button': 'button[type="submit"]',
            'orders_link': 'a[href*="/orders/"]',
            'order_item': '.order-item',
            'order_id': '.order-id',
            'order_status': '.order-status',
            'order_amount': '.order-amount',
            'order_buyer': '.order-buyer',
            'order_description': '.order-description',
            'chat_messages': '.chat-message',
            'message_input': 'textarea[name="message"]',
            'send_button': 'button[type="submit"]'
        }
    
    def setup_driver(self):
        """Настройка браузера"""
        try:
            options = uc.ChromeOptions()
            
            if self.headless:
                options.add_argument('--headless')
            
            # Настройки для стабильной работы
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Отключение уведомлений
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0,
                "profile.managed_default_content_settings.images": 2
            }
            options.add_experimental_option("prefs", prefs)
            
            self.driver = uc.Chrome(options=options)
            self.driver.implicitly_wait(10)
            
            print("✅ Браузер инициализирован")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка инициализации браузера: {e}")
            return False
    
    async def login(self) -> bool:
        """Авторизация на FunPay"""
        try:
            if not self.driver:
                if not self.setup_driver():
                    return False
            
            print("🔐 Авторизация на FunPay...")
            
            # Переход на страницу входа
            self.driver.get("https://funpay.com/account/login/")
            await asyncio.sleep(3)
            
            # Ввод логина
            login_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['login_input']))
            )
            login_input.clear()
            login_input.send_keys(self.login)
            
            # Ввод пароля
            password_input = self.driver.find_element(By.CSS_SELECTOR, self.selectors['password_input'])
            password_input.clear()
            password_input.send_keys(self.password)
            
            # Клик по кнопке входа
            login_button = self.driver.find_element(By.CSS_SELECTOR, self.selectors['login_button'])
            login_button.click()
            
            await asyncio.sleep(5)
            
            # Проверка успешного входа
            if "account/login" not in self.driver.current_url:
                self.is_logged_in = True
                print("✅ Авторизация успешна")
                return True
            else:
                print("❌ Ошибка авторизации")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка авторизации: {e}")
            return False
    
    async def get_orders(self) -> List[Dict]:
        """Получение списка заказов"""
        if not self.is_logged_in:
            if not await self.login():
                return []
        
        try:
            print("📋 Получение заказов...")
            
            # Переход к заказам
            self.driver.get("https://funpay.com/orders/")
            await asyncio.sleep(3)
            
            orders = []
            
            # Парсинг заказов со страницы
            order_elements = self.driver.find_elements(By.CSS_SELECTOR, ".order-row")
            
            for order_element in order_elements:
                try:
                    order_data = self._parse_order_element(order_element)
                    if order_data:
                        orders.append(order_data)
                except Exception as e:
                    print(f"Ошибка парсинга заказа: {e}")
                    continue
            
            print(f"✅ Найдено {len(orders)} заказов")
            return orders
            
        except Exception as e:
            print(f"❌ Ошибка получения заказов: {e}")
            return []
    
    def _parse_order_element(self, element) -> Optional[Dict]:
        """Парсинг отдельного элемента заказа"""
        try:
            # Извлечение данных заказа
            order_id = self._safe_extract_text(element, ".order-id")
            status = self._safe_extract_text(element, ".order-status")
            amount_text = self._safe_extract_text(element, ".order-sum")
            buyer = self._safe_extract_text(element, ".order-buyer")
            description = self._safe_extract_text(element, ".order-desc")
            
            # Парсинг суммы
            price = 0.0
            currency = "RUB"
            if amount_text:
                price_match = re.search(r'([\d.,]+)\s*([A-Za-z₽]+)', amount_text)
                if price_match:
                    price = float(price_match.group(1).replace(',', '.'))
                    currency = price_match.group(2).upper()
            
            # Извлечение telegram username из описания
            telegram_username = ""
            if description:
                telegram_match = re.search(r'@([a-zA-Z0-9_]{5,32})', description)
                if telegram_match:
                    telegram_username = f"@{telegram_match.group(1)}"
            
            return {
                'order_id': order_id or f"order_{int(time.time())}",
                'offer_id': 'stars_offer',  # Константа для Stars
                'quantity': 1,
                'buyer_username': buyer or 'unknown',
                'buyer_funpay_login': buyer or 'unknown',
                'total_price': price,
                'currency': currency,
                'status': 'PAID' if 'оплачен' in status.lower() else 'NEW',
                'created_at': datetime.now().isoformat(),
                'attached_telegram_username': telegram_username,
                'stars_amount_total': self._extract_stars_amount(description or "")
            }
            
        except Exception as e:
            print(f"Ошибка парсинга элемента заказа: {e}")
            return None
    
    def _safe_extract_text(self, element, selector: str) -> str:
        """Безопасное извлечение текста из элемента"""
        try:
            sub_element = element.find_element(By.CSS_SELECTOR, selector)
            return sub_element.text.strip()
        except:
            return ""
    
    def _extract_stars_amount(self, description: str) -> int:
        """Извлечение количества звёзд из описания"""
        # Ищем паттерны типа "100 stars", "500 звёзд", "1000⭐"
        patterns = [
            r'(\d+)\s*stars?',
            r'(\d+)\s*звёзд?',
            r'(\d+)\s*⭐',
            r'(\d+)\s*telegram\s*stars?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description.lower())
            if match:
                return int(match.group(1))
        
        # Значение по умолчанию
        return 100
    
    async def get_order_details(self, order_id: str) -> Optional[Dict]:
        """Получение деталей конкретного заказа"""
        try:
            print(f"📋 Получение деталей заказа {order_id}...")
            
            # Переход к заказу
            order_url = f"https://funpay.com/orders/{order_id}/"
            self.driver.get(order_url)
            await asyncio.sleep(3)
            
            # Парсинг деталей заказа
            order_details = self._parse_order_page()
            
            if order_details:
                order_details['order_id'] = order_id
                print("✅ Детали заказа получены")
                return order_details
            else:
                print("❌ Не удалось получить детали заказа")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка получения деталей заказа: {e}")
            return None
    
    def _parse_order_page(self) -> Optional[Dict]:
        """Парсинг страницы заказа"""
        try:
            # Получение статуса заказа
            status_element = self.driver.find_element(By.CSS_SELECTOR, ".order-status, .badge")
            status = status_element.text.strip() if status_element else "unknown"
            
            # Получение суммы
            amount_element = self.driver.find_element(By.CSS_SELECTOR, ".order-sum, .sum")
            amount_text = amount_element.text.strip() if amount_element else "0"
            
            # Парсинг сообщений чата для получения telegram username
            chat_messages = self.driver.find_elements(By.CSS_SELECTOR, ".chat-msg-text")
            telegram_username = ""
            
            for message in chat_messages:
                message_text = message.text
                telegram_match = re.search(r'@([a-zA-Z0-9_]{5,32})', message_text)
                if telegram_match:
                    telegram_username = f"@{telegram_match.group(1)}"
                    break
            
            return {
                'status': 'PAID' if 'оплачен' in status.lower() else 'NEW',
                'attached_telegram_username': telegram_username,
                'payment_status': 'оплачен' in status.lower()
            }
            
        except Exception as e:
            print(f"Ошибка парсинга страницы заказа: {e}")
            return None
    
    async def verify_payment(self, order_id: str) -> Dict:
        """Проверка оплаты заказа"""
        try:
            order_details = await self.get_order_details(order_id)
            
            if order_details:
                return {
                    'paid': order_details.get('payment_status', False),
                    'paid_at': datetime.now().isoformat() if order_details.get('payment_status') else None,
                    'method': 'funpay',
                    'tx_id': f"funpay_{order_id}"
                }
            else:
                return {
                    'paid': False,
                    'paid_at': None,
                    'method': 'funpay',
                    'tx_id': None
                }
                
        except Exception as e:
            print(f"❌ Ошибка проверки оплаты: {e}")
            return {
                'paid': False,
                'paid_at': None,
                'method': 'funpay',
                'tx_id': None
            }
    
    async def send_message(self, order_id: str, message: str) -> bool:
        """Отправка сообщения в чат заказа"""
        try:
            print(f"💬 Отправка сообщения в заказ {order_id}...")
            
            # Переход к заказу
            order_url = f"https://funpay.com/orders/{order_id}/"
            self.driver.get(order_url)
            await asyncio.sleep(3)
            
            # Поиск поля ввода сообщения
            message_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[name='content'], .chat-input"))
            )
            
            # Ввод сообщения
            message_input.clear()
            message_input.send_keys(message)
            
            # Отправка сообщения
            send_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .btn-primary")
            send_button.click()
            
            await asyncio.sleep(2)
            
            print("✅ Сообщение отправлено")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка отправки сообщения: {e}")
            return False
    
    def close(self):
        """Закрытие браузера"""
        if self.driver:
            try:
                self.driver.quit()
                print("✅ Браузер закрыт")
            except:
                pass

# Mock данные для разработки/тестирования
class MockFunPayParser:
    def __init__(self, login: str, password: str, headless: bool = True):
        self.login_cred = login
        self.password = password
        self.is_logged_in = False
        print("🧪 Используется Mock FunPay Parser для разработки")
    
    async def login(self) -> bool:
        print("🔐 Mock: Авторизация на FunPay...")
        await asyncio.sleep(1)
        self.is_logged_in = True
        print("✅ Mock: Авторизация успешна")
        return True
    
    async def get_orders(self) -> List[Dict]:
        print("📋 Mock: Получение заказов...")
        await asyncio.sleep(1)
        
        # Возвращаем тестовые заказы
        mock_orders = [
            {
                'order_id': f'mock_order_{int(time.time())}',
                'offer_id': 'stars_offer',
                'quantity': 1,
                'buyer_username': 'test_buyer',
                'buyer_funpay_login': 'test_buyer_funpay',
                'total_price': 500.0,
                'currency': 'RUB',
                'status': 'PAID',
                'created_at': datetime.now().isoformat(),
                'attached_telegram_username': '@testuser',
                'stars_amount_total': 500
            }
        ]
        
        print(f"✅ Mock: Найдено {len(mock_orders)} заказов")
        return mock_orders
    
    async def get_order_details(self, order_id: str) -> Optional[Dict]:
        print(f"📋 Mock: Получение деталей заказа {order_id}...")
        await asyncio.sleep(1)
        
        return {
            'order_id': order_id,
            'offer_id': 'stars_offer',
            'quantity': 1,
            'buyer_username': 'test_buyer',
            'buyer_funpay_login': 'test_buyer_funpay',
            'total_price': 500.0,
            'currency': 'RUB',
            'status': 'PAID',
            'created_at': datetime.now().isoformat(),
            'attached_telegram_username': '@testuser',
            'stars_amount_total': 500,
            'payment_status': True
        }
    
    async def verify_payment(self, order_id: str) -> Dict:
        print(f"💳 Mock: Проверка оплаты заказа {order_id}...")
        await asyncio.sleep(1)
        
        return {
            'paid': True,
            'paid_at': datetime.now().isoformat(),
            'method': 'funpay',
            'tx_id': f'mock_tx_{order_id}'
        }
    
    async def send_message(self, order_id: str, message: str) -> bool:
        print(f"💬 Mock: Отправка сообщения в заказ {order_id}: {message[:50]}...")
        await asyncio.sleep(1)
        print("✅ Mock: Сообщение отправлено")
        return True
    
    def close(self):
        print("✅ Mock: Браузер закрыт")
        pass
