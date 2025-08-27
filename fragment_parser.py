"""
Парсер Fragment для автоматической отправки Telegram Stars
"""

import time
import asyncio
from datetime import datetime
from typing import Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc
import re

class FragmentParser:
    def __init__(self, phone_number: str, headless: bool = True):
        self.phone_number = phone_number
        self.headless = headless
        self.driver = None
        self.is_logged_in = False
        
        # Селекторы для элементов страницы Fragment
        self.selectors = {
            'phone_input': 'input[name="phone"]',
            'continue_button': 'button[type="submit"]',
            'code_input': 'input[name="code"]',
            'stars_balance': '.stars-balance, .balance-stars',
            'send_stars_button': '.send-stars, [data-action="send-stars"]',
            'recipient_input': 'input[name="username"], input[placeholder*="username"]',
            'amount_input': 'input[name="amount"], input[placeholder*="amount"]',
            'send_button': 'button[type="submit"], .btn-send',
            'success_message': '.success, .alert-success',
            'error_message': '.error, .alert-error'
        }
    
    def setup_driver(self):
        """Настройка браузера для Fragment"""
        try:
            options = uc.ChromeOptions()
            
            if self.headless:
                options.add_argument('--headless')
            
            # Настройки для работы с Fragment
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Отключение уведомлений
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0
            }
            options.add_experimental_option("prefs", prefs)
            
            self.driver = uc.Chrome(options=options)
            self.driver.implicitly_wait(10)
            
            print("✅ Браузер для Fragment инициализирован")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка инициализации браузера Fragment: {e}")
            return False
    
    async def login(self) -> bool:
        """Авторизация в Fragment через номер телефона"""
        try:
            if not self.driver:
                if not self.setup_driver():
                    return False
            
            print("🔐 Авторизация в Fragment...")
            
            # Переход на Fragment
            self.driver.get("https://fragment.com/")
            await asyncio.sleep(3)
            
            # Поиск кнопки входа
            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Log in')]"))
            )
            login_button.click()
            await asyncio.sleep(2)
            
            # Ввод номера телефона
            phone_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['phone_input']))
            )
            phone_input.clear()
            phone_input.send_keys(self.phone_number)
            
            # Нажатие кнопки продолжить
            continue_button = self.driver.find_element(By.CSS_SELECTOR, self.selectors['continue_button'])
            continue_button.click()
            
            print("📱 Код отправлен на телефон. Ожидание ввода кода...")
            
            # Ожидание ввода кода (пользователь должен ввести код вручную)
            print("⚠️ Введите код из Telegram в браузере и нажмите Enter здесь...")
            input("Нажмите Enter после ввода кода: ")
            
            await asyncio.sleep(5)
            
            # Проверка успешного входа
            if "fragment.com" in self.driver.current_url and "login" not in self.driver.current_url:
                self.is_logged_in = True
                print("✅ Авторизация в Fragment успешна")
                return True
            else:
                print("❌ Ошибка авторизации в Fragment")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка авторизации в Fragment: {e}")
            return False
    
    async def get_balance(self) -> Dict:
        """Получение баланса Stars"""
        if not self.is_logged_in:
            if not await self.login():
                return {'stars_balance': 0, 'daily_limit_left': 0}
        
        try:
            print("💰 Получение баланса Stars...")
            
            # Переход на страницу баланса
            self.driver.get("https://fragment.com/balance")
            await asyncio.sleep(3)
            
            # Поиск баланса Stars
            balance_text = "0"
            try:
                balance_element = self.driver.find_element(By.CSS_SELECTOR, self.selectors['stars_balance'])
                balance_text = balance_element.text
            except:
                # Альтернативные селекторы
                balance_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Stars') or contains(text(), '⭐')]")
                for element in balance_elements:
                    if re.search(r'\d+', element.text):
                        balance_text = element.text
                        break
            
            # Парсинг числа из текста баланса
            balance_match = re.search(r'([\d,]+)', balance_text.replace(',', ''))
            stars_balance = int(balance_match.group(1)) if balance_match else 0
            
            print(f"✅ Баланс Stars: {stars_balance:,}")
            
            return {
                'stars_balance': stars_balance,
                'daily_limit_left': 100000  # Примерный дневной лимит
            }
            
        except Exception as e:
            print(f"❌ Ошибка получения баланса: {e}")
            return {'stars_balance': 0, 'daily_limit_left': 0}
    
    async def transfer_stars(self, to_username: str, stars_amount: int, idempotency_key: str) -> Dict:
        """Отправка Stars пользователю"""
        if not self.is_logged_in:
            if not await self.login():
                return {
                    'ok': False,
                    'error_code': 'auth_failed',
                    'error_message': 'Не удалось авторизоваться'
                }
        
        try:
            print(f"⭐ Отправка {stars_amount} Stars пользователю {to_username}...")
            
            # Переход на страницу отправки Stars
            self.driver.get("https://fragment.com/stars")
            await asyncio.sleep(3)
            
            # Поиск кнопки "Send Stars" или аналогичной
            send_button = None
            try:
                send_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Send') or contains(text(), 'Transfer')]"))
                )
            except:
                # Альтернативные варианты поиска кнопки
                send_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in send_buttons:
                    if any(word in btn.text.lower() for word in ['send', 'transfer', 'отправить']):
                        send_button = btn
                        break
            
            if not send_button:
                return {
                    'ok': False,
                    'error_code': 'send_button_not_found',
                    'error_message': 'Кнопка отправки не найдена'
                }
            
            send_button.click()
            await asyncio.sleep(2)
            
            # Ввод получателя
            recipient_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.selectors['recipient_input']))
            )
            recipient_input.clear()
            recipient_input.send_keys(to_username.replace('@', ''))  # Убираем @ если есть
            
            # Ввод количества Stars
            amount_input = self.driver.find_element(By.CSS_SELECTOR, self.selectors['amount_input'])
            amount_input.clear()
            amount_input.send_keys(str(stars_amount))
            
            # Отправка
            final_send_button = self.driver.find_element(By.CSS_SELECTOR, self.selectors['send_button'])
            final_send_button.click()
            
            await asyncio.sleep(5)
            
            # Проверка результата
            try:
                success_element = self.driver.find_element(By.CSS_SELECTOR, self.selectors['success_message'])
                if success_element:
                    transfer_id = f"fragment_{idempotency_key}_{int(time.time())}"
                    print(f"✅ Stars отправлены успешно. ID: {transfer_id}")
                    
                    return {
                        'ok': True,
                        'transfer_id': transfer_id,
                        'error_code': None,
                        'error_message': None
                    }
            except:
                pass
            
            # Проверка на ошибку
            try:
                error_element = self.driver.find_element(By.CSS_SELECTOR, self.selectors['error_message'])
                error_message = error_element.text if error_element else "Неизвестная ошибка"
                
                print(f"❌ Ошибка отправки Stars: {error_message}")
                
                return {
                    'ok': False,
                    'error_code': 'transfer_failed',
                    'error_message': error_message
                }
            except:
                pass
            
            # Если нет явного сообщения об успехе или ошибке
            print("⚠️ Статус отправки неопределён")
            return {
                'ok': False,
                'error_code': 'status_unknown',
                'error_message': 'Не удалось определить статус отправки'
            }
            
        except Exception as e:
            print(f"❌ Ошибка отправки Stars: {e}")
            return {
                'ok': False,
                'error_code': 'exception',
                'error_message': str(e)
            }
    
    def close(self):
        """Закрытие браузера"""
        if self.driver:
            try:
                self.driver.quit()
                print("✅ Браузер Fragment закрыт")
            except:
                pass

# Mock данные для разработки/тестирования
class MockFragmentParser:
    def __init__(self, phone_number: str, headless: bool = True):
        self.phone_number = phone_number
        self.is_logged_in = False
        print("🧪 Используется Mock Fragment Parser для разработки")
    
    async def login(self) -> bool:
        print("🔐 Mock: Авторизация в Fragment...")
        await asyncio.sleep(1)
        self.is_logged_in = True
        print("✅ Mock: Авторизация в Fragment успешна")
        return True
    
    async def get_balance(self) -> Dict:
        print("💰 Mock: Получение баланса Stars...")
        await asyncio.sleep(1)
        
        balance = {
            'stars_balance': 50000,
            'daily_limit_left': 100000
        }
        
        print(f"✅ Mock: Баланс Stars: {balance['stars_balance']:,}")
        return balance
    
    async def transfer_stars(self, to_username: str, stars_amount: int, idempotency_key: str) -> Dict:
        print(f"⭐ Mock: Отправка {stars_amount} Stars пользователю {to_username}...")
        await asyncio.sleep(2)
        
        # Имитация успешной отправки
        transfer_id = f"mock_transfer_{idempotency_key}_{int(time.time())}"
        
        print(f"✅ Mock: Stars отправлены успешно. ID: {transfer_id}")
        
        return {
            'ok': True,
            'transfer_id': transfer_id,
            'error_code': None,
            'error_message': None
        }
    
    def close(self):
        print("✅ Mock: Браузер Fragment закрыт")
        pass
