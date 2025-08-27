import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

# Business Rules
CURRENCY = os.getenv('CURRENCY', 'RUB')
PAYMENT_WAIT_MINUTES = int(os.getenv('PAYMENT_WAIT_MINUTES', '30'))
REMIND_EACH_MIN = int(os.getenv('REMIND_EACH_MIN', '10'))
AUTO_CLOSE_MIN = int(os.getenv('AUTO_CLOSE_MIN', '120'))
FRAGMENT_MIN = int(os.getenv('FRAGMENT_MIN', '50'))
FRAGMENT_MAX = int(os.getenv('FRAGMENT_MAX', '20000'))
MAX_RETRY = int(os.getenv('MAX_RETRY', '5'))
MAX_RETRY_VERIFY = int(os.getenv('MAX_RETRY_VERIFY', '5'))
RETRY_AFTER_MIN = int(os.getenv('RETRY_AFTER_MIN', '30'))

# FunPay Parser Configuration
FUNPAY_LOGIN = os.getenv('FUNPAY_LOGIN')
FUNPAY_PASSWORD = os.getenv('FUNPAY_PASSWORD')

# Fragment Parser Configuration
FRAGMENT_PHONE = os.getenv('FRAGMENT_PHONE')

# Parser Settings
USE_MOCK_PARSERS = os.getenv('USE_MOCK_PARSERS', 'true').lower() == 'true'
BROWSER_HEADLESS = os.getenv('BROWSER_HEADLESS', 'true').lower() == 'true'

# Database Configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', 'bot_database.db')

# Order Statuses
class OrderStatus:
    NEW = "NEW"
    WAITING_PAYMENT = "WAITING_PAYMENT"
    PAID = "PAID"
    FULFILLING = "FULFILLING"
    FULFILLED = "FULFILLED"
    NEEDS_USERNAME = "NEEDS_USERNAME"
    NEEDS_BALANCE = "NEEDS_BALANCE"
    FAILED = "FAILED"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"

# Fulfillment Statuses
class FulfillmentStatus:
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
