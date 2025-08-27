import aiohttp
import asyncio
import hashlib
import uuid
import os
from datetime import datetime
from typing import Dict, List, Optional
from config import MAX_RETRY, FRAGMENT_MAX, FRAGMENT_MIN

# Импорт парсеров
try:
    from funpay_parser import FunPayParser, MockFunPayParser
    from fragment_parser import FragmentParser, MockFragmentParser
    PARSERS_AVAILABLE = True
except ImportError:
    print("⚠️ Парсеры не найдены, используются mock данные")
    PARSERS_AVAILABLE = False

class FunPayAPI:
    def __init__(self):
        # Получение данных для авторизации из переменных окружения
        self.funpay_login = os.getenv('FUNPAY_LOGIN', '')
        self.funpay_password = os.getenv('FUNPAY_PASSWORD', '')
        self.use_mock = os.getenv('USE_MOCK_PARSERS', 'true').lower() == 'true'
        
        # Инициализация парсера
        if PARSERS_AVAILABLE and not self.use_mock and self.funpay_login and self.funpay_password:
            self.parser = FunPayParser(self.funpay_login, self.funpay_password, headless=True)
            print("✅ Инициализирован реальный FunPay парсер")
        else:
            self.parser = MockFunPayParser(self.funpay_login, self.funpay_password, headless=True)
            print("🧪 Инициализирован Mock FunPay парсер")
    
    def __del__(self):
        """Очистка ресурсов при удалении объекта"""
        if hasattr(self, 'parser') and self.parser:
            try:
                self.parser.close()
            except:
                pass
    
    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None, retries: int = MAX_RETRY):
        """Make HTTP request with retry logic"""
        session = await self._get_session()
        
        for attempt in range(retries):
            try:
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                
                if method.upper() == 'GET':
                    async with session.get(f"{self.api_url}{endpoint}", headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:  # Rate limit
                            wait_time = 2 ** attempt
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            response.raise_for_status()
                else:
                    async with session.post(f"{self.api_url}{endpoint}", 
                                          headers=headers, json=data) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:  # Rate limit
                            wait_time = 2 ** attempt
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            response.raise_for_status()
                            
            except Exception as e:
                if attempt == retries - 1:
                    raise e
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
        
        raise Exception(f"Failed after {retries} attempts")
    
    async def list_offers(self) -> List[Dict]:
        """Get list of offers from FunPay"""
        try:
            # Получение заказов через парсер
            orders = await self.parser.get_orders()
            
            # Преобразование заказов в формат офферов для совместимости
            offers = []
            for order in orders:
                if order.get('stars_amount_total', 0) > 0:
                    offers.append({
                        'offer_id': f"stars_{order['stars_amount_total']}",
                        'title': f"{order['stars_amount_total']} Telegram Stars",
                        'stars_amount': order['stars_amount_total'],
                        'price': order['total_price'],
                        'currency': order['currency'],
                        'is_active': True
                    })
            
            # Если нет заказов, возвращаем стандартные офферы
            if not offers:
                offers = [
                    {
                        'offer_id': 'offer_100',
                        'title': '100 Telegram Stars',
                        'stars_amount': 100,
                        'price': 100.0,
                        'currency': 'RUB',
                        'is_active': True
                    },
                    {
                        'offer_id': 'offer_500',
                        'title': '500 Telegram Stars',
                        'stars_amount': 500,
                        'price': 450.0,
                        'currency': 'RUB',
                        'is_active': True
                    },
                    {
                        'offer_id': 'offer_1000',
                        'title': '1000 Telegram Stars',
                        'stars_amount': 1000,
                        'price': 850.0,
                        'currency': 'RUB',
                        'is_active': True
                    }
                ]
            
            return offers
            
        except Exception as e:
            print(f"Ошибка получения офферов: {e}")
            # Возвращаем базовые офферы в случае ошибки
            return [
                {
                    'offer_id': 'offer_100',
                    'title': '100 Telegram Stars',
                    'stars_amount': 100,
                    'price': 100.0,
                    'currency': 'RUB',
                    'is_active': True
                }
            ]
    
    async def get_order(self, order_id: str) -> Dict:
        """Get order details from FunPay"""
        try:
            # Получение деталей заказа через парсер
            order_details = await self.parser.get_order_details(order_id)
            
            if order_details:
                return order_details
            else:
                # Если заказ не найден, возвращаем базовые данные
                return {
                    'order_id': order_id,
                    'offer_id': 'stars_offer',
                    'quantity': 1,
                    'buyer_username': 'unknown_user',
                    'buyer_funpay_login': 'unknown_funpay',
                    'total_price': 100.0,
                    'currency': 'RUB',
                    'status': 'NEW',
                    'created_at': datetime.now().isoformat(),
                    'attached_telegram_username': '',
                    'stars_amount_total': 100
                }
                
        except Exception as e:
            print(f"Ошибка получения заказа {order_id}: {e}")
            return {
                'order_id': order_id,
                'offer_id': 'stars_offer',
                'quantity': 1,
                'buyer_username': 'error_user',
                'buyer_funpay_login': 'error_funpay',
                'total_price': 0.0,
                'currency': 'RUB',
                'status': 'ERROR',
                'created_at': datetime.now().isoformat(),
                'attached_telegram_username': '',
                'stars_amount_total': 0
            }
    
    async def verify_payment(self, order_id: str) -> Dict:
        """Verify payment status"""
        try:
            # Проверка оплаты через парсер
            payment_status = await self.parser.verify_payment(order_id)
            return payment_status
            
        except Exception as e:
            print(f"Ошибка проверки оплаты {order_id}: {e}")
            return {
                'paid': False,
                'paid_at': None,
                'method': 'funpay',
                'tx_id': None
            }

class FragmentAPI:
    def __init__(self):
        # Получение данных для авторизации из переменных окружения
        self.fragment_phone = os.getenv('FRAGMENT_PHONE', '')
        self.use_mock = os.getenv('USE_MOCK_PARSERS', 'true').lower() == 'true'
        
        # Инициализация парсера
        if PARSERS_AVAILABLE and not self.use_mock and self.fragment_phone:
            self.parser = FragmentParser(self.fragment_phone, headless=True)
            print("✅ Инициализирован реальный Fragment парсер")
        else:
            self.parser = MockFragmentParser(self.fragment_phone, headless=True)
            print("🧪 Инициализирован Mock Fragment парсер")
    
    def __del__(self):
        """Очистка ресурсов при удалении объекта"""
        if hasattr(self, 'parser') and self.parser:
            try:
                self.parser.close()
            except:
                pass
    
    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _make_request(self, method: str, endpoint: str, data: Dict = None, retries: int = MAX_RETRY):
        """Make HTTP request with retry logic"""
        session = await self._get_session()
        
        for attempt in range(retries):
            try:
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                
                if method.upper() == 'GET':
                    async with session.get(f"{self.api_url}{endpoint}", headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:  # Rate limit
                            wait_time = 2 ** attempt
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            response.raise_for_status()
                else:
                    async with session.post(f"{self.api_url}{endpoint}", 
                                          headers=headers, json=data) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 429:  # Rate limit
                            wait_time = 2 ** attempt
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            response.raise_for_status()
                            
            except Exception as e:
                if attempt == retries - 1:
                    raise e
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
        
        raise Exception(f"Failed after {retries} attempts")
    
    async def get_balance(self) -> Dict:
        """Get Fragment balance"""
        try:
            # Получение баланса через парсер
            balance = await self.parser.get_balance()
            return balance
            
        except Exception as e:
            print(f"Ошибка получения баланса Fragment: {e}")
            return {
                'stars_balance': 0,
                'daily_limit_left': 0
            }
    
    async def transfer_stars(self, to_username: str, stars_amount: int, idempotency_key: str) -> Dict:
        """Transfer stars via Fragment"""
        try:
            # Отправка Stars через парсер
            result = await self.parser.transfer_stars(to_username, stars_amount, idempotency_key)
            return result
            
        except Exception as e:
            print(f"Ошибка отправки Stars: {e}")
            return {
                'ok': False,
                'transfer_id': None,
                'error_code': 'exception',
                'error_message': str(e)
            }

class NotificationService:
    def __init__(self, bot):
        self.bot = bot
    
    async def notify_user(self, chat_id: int, message: str):
        """Send notification to user"""
        try:
            await self.bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
        except Exception as e:
            print(f"Failed to notify user {chat_id}: {e}")
    
    async def notify_admin(self, message: str):
        """Send notification to all admins"""
        from config import ADMIN_IDS
        for admin_id in ADMIN_IDS:
            try:
                await self.bot.send_message(chat_id=admin_id, text=message, parse_mode='HTML')
            except Exception as e:
                print(f"Failed to notify admin {admin_id}: {e}")

class Utils:
    @staticmethod
    def sleep(ms: int):
        """Sleep for specified milliseconds"""
        return asyncio.sleep(ms / 1000)
    
    @staticmethod
    def now() -> str:
        """Get current time in ISO format"""
        return datetime.now().isoformat()
    
    @staticmethod
    def generate_idempotency_key(order_id: str, to_username: str, stars_amount: int) -> str:
        """Generate deterministic idempotency key"""
        key_data = f"{order_id}:{to_username}:{stars_amount}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate Telegram username format"""
        if not username:
            return False
        
        # Remove @ if present
        if username.startswith('@'):
            username = username[1:]
        
        # Check length and characters
        if len(username) < 5 or len(username) > 32:
            return False
        
        # Check if contains only letters, numbers, and underscores
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False
        
        return True
    
    @staticmethod
    def normalize_username(username: str) -> str:
        """Normalize username (add @ if missing)"""
        if not username:
            return username
        
        if not username.startswith('@'):
            username = '@' + username
        
        return username
    
    @staticmethod
    def split_stars_into_batches(stars_total: int, max_per_batch: int = FRAGMENT_MAX) -> List[int]:
        """Split total stars into batches"""
        if stars_total <= max_per_batch:
            return [stars_total]
        
        batches = []
        remaining = stars_total
        
        while remaining > 0:
            batch_size = min(remaining, max_per_batch)
            batches.append(batch_size)
            remaining -= batch_size
        
        return batches
    
    @staticmethod
    def mask_transaction_id(tx_id: str, visible_chars: int = 6) -> str:
        """Mask transaction ID for user messages"""
        if not tx_id or len(tx_id) <= visible_chars:
            return tx_id
        
        return f"...{tx_id[-visible_chars:]}"

# Global instances
funpay = FunPayAPI()
fragment = FragmentAPI()
utils = Utils()
