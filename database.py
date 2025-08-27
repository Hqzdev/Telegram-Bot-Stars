import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from config import DATABASE_PATH, OrderStatus, FulfillmentStatus

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Orders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    offer_id TEXT,
                    quantity INTEGER,
                    buyer_username TEXT,
                    buyer_funpay_login TEXT,
                    total_price REAL,
                    currency TEXT,
                    status TEXT,
                    attached_telegram_username TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    stars_amount_total INTEGER
                )
            ''')
            
            # Fulfillments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fulfillments (
                    fulfillment_id TEXT PRIMARY KEY,
                    order_id TEXT,
                    to_username TEXT,
                    stars_total INTEGER,
                    batches TEXT,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    notes TEXT,
                    FOREIGN KEY (order_id) REFERENCES orders (order_id)
                )
            ''')
            
            # Offers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS offers (
                    offer_id TEXT PRIMARY KEY,
                    title TEXT,
                    stars_amount INTEGER,
                    price REAL,
                    currency TEXT,
                    is_active BOOLEAN,
                    updated_at TEXT
                )
            ''')
            
            # Order logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    order_id TEXT,
                    stars_amount INTEGER,
                    price_original REAL,
                    currency_original TEXT,
                    price_rub REAL,
                    buyer_username TEXT,
                    to_username TEXT,
                    fulfillment_id TEXT,
                    status TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def create_fulfillment(self, record: Dict) -> str:
        """Create a new fulfillment record"""
        fulfillment_id = record.get('fulfillment_id', str(uuid.uuid4()))
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO fulfillments 
                (fulfillment_id, order_id, to_username, stars_total, batches, status, created_at, updated_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fulfillment_id,
                record['order_id'],
                record['to_username'],
                record['stars_total'],
                json.dumps(record.get('batches', [])),
                record['status'],
                record['created_at'],
                record['updated_at'],
                record.get('notes', '')
            ))
            conn.commit()
        
        return fulfillment_id
    
    def update_fulfillment_status(self, fulfillment_id: str, status: str, meta: Dict = None):
        """Update fulfillment status and metadata"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            update_data = {
                'status': status,
                'updated_at': datetime.now().isoformat()
            }
            
            if meta:
                if 'batches' in meta:
                    update_data['batches'] = json.dumps(meta['batches'])
                if 'notes' in meta:
                    update_data['notes'] = meta['notes']
            
            set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
            values = list(update_data.values()) + [fulfillment_id]
            
            cursor.execute(f'''
                UPDATE fulfillments 
                SET {set_clause}
                WHERE fulfillment_id = ?
            ''', values)
            
            conn.commit()
    
    def get_fulfillment(self, fulfillment_id: str) -> Optional[Dict]:
        """Get fulfillment by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT fulfillment_id, order_id, to_username, stars_total, 
                       batches, status, created_at, updated_at, notes
                FROM fulfillments 
                WHERE fulfillment_id = ?
            ''', (fulfillment_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'fulfillment_id': row[0],
                    'order_id': row[1],
                    'to_username': row[2],
                    'stars_total': row[3],
                    'batches': json.loads(row[4]) if row[4] else [],
                    'status': row[5],
                    'created_at': row[6],
                    'updated_at': row[7],
                    'notes': row[8]
                }
        return None
    
    def get_fulfillment_by_order(self, order_id: str) -> Optional[Dict]:
        """Get fulfillment by order ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT fulfillment_id, order_id, to_username, stars_total, 
                       batches, status, created_at, updated_at, notes
                FROM fulfillments 
                WHERE order_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (order_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'fulfillment_id': row[0],
                    'order_id': row[1],
                    'to_username': row[2],
                    'stars_total': row[3],
                    'batches': json.loads(row[4]) if row[4] else [],
                    'status': row[5],
                    'created_at': row[6],
                    'updated_at': row[7],
                    'notes': row[8]
                }
        return None
    
    def save_order(self, order_data: Dict):
        """Save or update order data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO orders 
                (order_id, offer_id, quantity, buyer_username, buyer_funpay_login, 
                 total_price, currency, status, attached_telegram_username, 
                 created_at, updated_at, stars_amount_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order_data['order_id'],
                order_data['offer_id'],
                order_data['quantity'],
                order_data['buyer_username'],
                order_data['buyer_funpay_login'],
                order_data['total_price'],
                order_data['currency'],
                order_data['status'],
                order_data.get('attached_telegram_username', ''),
                order_data['created_at'],
                order_data.get('updated_at', datetime.now().isoformat()),
                order_data.get('stars_amount_total', 0)
            ))
            conn.commit()
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT order_id, offer_id, quantity, buyer_username, buyer_funpay_login,
                       total_price, currency, status, attached_telegram_username,
                       created_at, updated_at, stars_amount_total
                FROM orders 
                WHERE order_id = ?
            ''', (order_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'order_id': row[0],
                    'offer_id': row[1],
                    'quantity': row[2],
                    'buyer_username': row[3],
                    'buyer_funpay_login': row[4],
                    'total_price': row[5],
                    'currency': row[6],
                    'status': row[7],
                    'attached_telegram_username': row[8],
                    'created_at': row[9],
                    'updated_at': row[10],
                    'stars_amount_total': row[11]
                }
        return None
    
    def update_order_status(self, order_id: str, status: str):
        """Update order status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE orders 
                SET status = ?, updated_at = ?
                WHERE order_id = ?
            ''', (status, datetime.now().isoformat(), order_id))
            conn.commit()
    
    def get_recent_orders(self, limit: int = 10) -> List[Dict]:
        """Get recent orders for admin panel"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT order_id, offer_id, quantity, buyer_username, status,
                       total_price, currency, created_at, stars_amount_total
                FROM orders 
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            return [{
                'order_id': row[0],
                'offer_id': row[1],
                'quantity': row[2],
                'buyer_username': row[3],
                'status': row[4],
                'total_price': row[5],
                'currency': row[6],
                'created_at': row[7],
                'stars_amount_total': row[8]
            } for row in rows]
    
    def save_offers(self, offers: List[Dict]):
        """Save or update offers"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for offer in offers:
                cursor.execute('''
                    INSERT OR REPLACE INTO offers 
                    (offer_id, title, stars_amount, price, currency, is_active, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    offer['offer_id'],
                    offer['title'],
                    offer['stars_amount'],
                    offer['price'],
                    offer['currency'],
                    offer['is_active'],
                    datetime.now().isoformat()
                ))
            conn.commit()
    
    def get_active_offers(self) -> List[Dict]:
        """Get active offers"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT offer_id, title, stars_amount, price, currency, is_active
                FROM offers 
                WHERE is_active = 1
                ORDER BY stars_amount
            ''')
            
            rows = cursor.fetchall()
            return [{
                'offer_id': row[0],
                'title': row[1],
                'stars_amount': row[2],
                'price': row[3],
                'currency': row[4],
                'is_active': bool(row[5])
            } for row in rows]
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

# Global database instance
db = Database()
