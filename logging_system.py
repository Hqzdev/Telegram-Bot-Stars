import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal

from config import CURRENCY
from database import db
from integrations import utils

class OrderLogger:
    def __init__(self, notification_service):
        self.notification_service = notification_service
        
        # Настройка логирования
        self.setup_logging()
        
        # Статистика
        self.total_revenue = Decimal('0')
        self.total_stars_sold = 0
        self.total_orders = 0
    
    def setup_logging(self):
        """Настройка системы логирования"""
        # Создание директории для логов
        import os
        os.makedirs('logs', exist_ok=True)
        
        # Настройка основного логгера
        self.logger = logging.getLogger('telegram_stars_bot')
        self.logger.setLevel(logging.INFO)
        
        # Хендлер для файла
        file_handler = logging.FileHandler('logs/bot_operations.log', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Хендлер для консоли
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Форматтер
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Добавление хендлеров
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    async def log_order_completion(self, order_data: Dict, fulfillment_data: Dict):
        """Логирование выполненного заказа"""
        order_id = order_data['order_id']
        stars_amount = order_data['stars_amount_total']
        price_rub = order_data['total_price']
        currency = order_data['currency']
        buyer_username = order_data['buyer_username']
        to_username = order_data['attached_telegram_username']
        
        # Конвертация в рубли (если валюта не рубли)
        price_rub_converted = self._convert_to_rub(price_rub, currency)
        
        # Логирование в файл
        log_entry = {
            'timestamp': utils.now(),
            'order_id': order_id,
            'stars_amount': stars_amount,
            'price_original': price_rub,
            'currency_original': currency,
            'price_rub': float(price_rub_converted),
            'buyer_username': buyer_username,
            'to_username': to_username,
            'fulfillment_id': fulfillment_data.get('fulfillment_id'),
            'status': 'completed'
        }
        
        self.logger.info(f"Order completed: {json.dumps(log_entry, ensure_ascii=False)}")
        
        # Сохранение в базу данных
        self._save_order_log(log_entry)
        
        # Обновление статистики
        self._update_statistics(stars_amount, price_rub_converted)
        
        # Уведомление админа
        await self._notify_admin_completion(log_entry)
    
    def _convert_to_rub(self, amount: float, currency: str) -> Decimal:
        """Конвертация валюты в рубли"""
        # Простые курсы валют (в реальном проекте лучше использовать API)
        rates = {
            'RUB': 1.0,
            'USD': 95.0,  # Примерный курс
            'EUR': 105.0, # Примерный курс
            'USDT': 95.0, # Примерный курс
        }
        
        rate = rates.get(currency.upper(), 1.0)
        return Decimal(str(amount * rate))
    
    def _save_order_log(self, log_entry: Dict):
        """Сохранение лога заказа в базу данных"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO order_logs 
                    (timestamp, order_id, stars_amount, price_original, currency_original, 
                     price_rub, buyer_username, to_username, fulfillment_id, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    log_entry['timestamp'],
                    log_entry['order_id'],
                    log_entry['stars_amount'],
                    log_entry['price_original'],
                    log_entry['currency_original'],
                    log_entry['price_rub'],
                    log_entry['buyer_username'],
                    log_entry['to_username'],
                    log_entry['fulfillment_id'],
                    log_entry['status']
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error saving order log: {e}")
    
    def _update_statistics(self, stars_amount: int, price_rub: Decimal):
        """Обновление общей статистики"""
        self.total_stars_sold += stars_amount
        self.total_revenue += price_rub
        self.total_orders += 1
    
    async def _notify_admin_completion(self, log_entry: Dict):
        """Уведомление админа о выполненном заказе"""
        message = f"""🎉 <b>Заказ выполнен!</b>

📋 <b>Детали заказа:</b>
• ID: {log_entry['order_id']}
• Звёзды: {log_entry['stars_amount']:,} ⭐
• Цена: {log_entry['price_original']} {log_entry['currency_original']}
• Цена в рублях: {log_entry['price_rub']:,.2f} ₽
• Покупатель: {log_entry['buyer_username']}
• Получатель: {log_entry['to_username']}

💰 <b>Доход:</b> +{log_entry['price_rub']:,.2f} ₽

📊 <b>Общая статистика:</b>
• Всего заказов: {self.total_orders}
• Всего звёзд: {self.total_stars_sold:,} ⭐
• Общий доход: {self.total_revenue:,.2f} ₽"""

        await self.notification_service.notify_admin(message)
    
    async def get_monthly_statistics(self, year: int = None, month: int = None) -> Dict:
        """Получение статистики за месяц"""
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month
        
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_orders,
                        SUM(stars_amount) as total_stars,
                        SUM(price_rub) as total_revenue
                    FROM order_logs 
                    WHERE timestamp >= ? AND timestamp < ? AND status = 'completed'
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                result = cursor.fetchone()
                
                if result and result[0]:
                    return {
                        'year': year,
                        'month': month,
                        'total_orders': result[0],
                        'total_stars': result[1] or 0,
                        'total_revenue': float(result[2] or 0)
                    }
                else:
                    return {
                        'year': year,
                        'month': month,
                        'total_orders': 0,
                        'total_stars': 0,
                        'total_revenue': 0.0
                    }
                    
        except Exception as e:
            self.logger.error(f"Error getting monthly statistics: {e}")
            return {
                'year': year,
                'month': month,
                'total_orders': 0,
                'total_stars': 0,
                'total_revenue': 0.0,
                'error': str(e)
            }
    
    async def get_all_time_statistics(self) -> Dict:
        """Получение общей статистики за всё время"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_orders,
                        SUM(stars_amount) as total_stars,
                        SUM(price_rub) as total_revenue
                    FROM order_logs 
                    WHERE status = 'completed'
                ''')
                
                result = cursor.fetchone()
                
                if result and result[0]:
                    return {
                        'total_orders': result[0],
                        'total_stars': result[1] or 0,
                        'total_revenue': float(result[2] or 0)
                    }
                else:
                    return {
                        'total_orders': 0,
                        'total_stars': 0,
                        'total_revenue': 0.0
                    }
                    
        except Exception as e:
            self.logger.error(f"Error getting all-time statistics: {e}")
            return {
                'total_orders': 0,
                'total_stars': 0,
                'total_revenue': 0.0,
                'error': str(e)
            }
    
    def log_error(self, error_message: str, order_id: str = None, context: Dict = None):
        """Логирование ошибок"""
        log_data = {
            'timestamp': utils.now(),
            'error': error_message,
            'order_id': order_id,
            'context': context or {}
        }
        
        self.logger.error(f"Error occurred: {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_admin_action(self, admin_id: int, action: str, details: Dict = None):
        """Логирование действий администратора"""
        log_data = {
            'timestamp': utils.now(),
            'admin_id': admin_id,
            'action': action,
            'details': details or {}
        }
        
        self.logger.info(f"Admin action: {json.dumps(log_data, ensure_ascii=False)}")
    
    def get_recent_orders(self, limit: int = 10) -> List[Dict]:
        """Получение последних заказов"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp, order_id, stars_amount, price_rub, buyer_username, to_username
                    FROM order_logs 
                    WHERE status = 'completed'
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                return [{
                    'timestamp': row[0],
                    'order_id': row[1],
                    'stars_amount': row[2],
                    'price_rub': row[3],
                    'buyer_username': row[4],
                    'to_username': row[5]
                } for row in rows]
                
        except Exception as e:
            self.logger.error(f"Error getting recent orders: {e}")
            return []
