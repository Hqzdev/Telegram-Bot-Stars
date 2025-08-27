import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from config import (
    OrderStatus, FulfillmentStatus, CURRENCY, PAYMENT_WAIT_MINUTES,
    REMIND_EACH_MIN, FRAGMENT_MIN, FRAGMENT_MAX, MAX_RETRY, MAX_RETRY_VERIFY
)
from database import db
from integrations import funpay, fragment, utils
from message_templates import MessageTemplates
from logging_system import OrderLogger

class OrderProcessor:
    def __init__(self, notification_service):
        self.notification_service = notification_service
        self.message_templates = MessageTemplates()
        self.order_logger = OrderLogger(notification_service)
        self.processing_orders = set()  # Prevent duplicate processing
    
    async def process_order(self, order_id: str, chat_id: int = None):
        """Main order processing method"""
        if order_id in self.processing_orders:
            return
        
        self.processing_orders.add(order_id)
        
        try:
            # Step 1: Get order details
            order_data = await self._get_order_details(order_id)
            if not order_data:
                await self._handle_error(order_id, "Order not found", chat_id)
                return
            
            # Save order to database
            db.save_order(order_data)
            
            # Step 2: Check username
            if not self._validate_username(order_data.get('attached_telegram_username')):
                await self._handle_needs_username(order_data, chat_id)
                return
            
            # Step 3: Check payment
            payment_status = await self._check_payment(order_id)
            if not payment_status['paid']:
                await self._handle_waiting_payment(order_data, chat_id)
                return
            
            # Step 4: Check Fragment balance
            balance = await fragment.get_balance()
            stars_total = order_data['stars_amount_total']
            
            if balance['stars_balance'] < stars_total:
                await self._handle_needs_balance(order_data, balance, chat_id)
                return
            
            # Step 5: Process fulfillment
            await self._process_fulfillment(order_data, chat_id)
            
        except Exception as e:
            await self._handle_error(order_id, str(e), chat_id)
        finally:
            self.processing_orders.discard(order_id)
    
    async def _get_order_details(self, order_id: str) -> Optional[Dict]:
        """Get order details from FunPay"""
        try:
            order_data = await funpay.get_order(order_id)
            
            # Get offer details to calculate total stars
            offers = await funpay.list_offers()
            offer = next((o for o in offers if o['offer_id'] == order_data['offer_id']), None)
            
            if offer:
                order_data['stars_amount_total'] = offer['stars_amount'] * order_data['quantity']
            else:
                order_data['stars_amount_total'] = 0
            
            return order_data
        except Exception as e:
            print(f"Error getting order details: {e}")
            return None
    
    def _validate_username(self, username: str) -> bool:
        """Validate Telegram username"""
        return utils.validate_username(username)
    
    async def _check_payment(self, order_id: str, retries: int = MAX_RETRY_VERIFY) -> Dict:
        """Check payment status with retries"""
        for attempt in range(retries):
            try:
                payment_status = await funpay.verify_payment(order_id)
                return payment_status
            except Exception as e:
                if attempt == retries - 1:
                    raise e
                await utils.sleep(1000 * (2 ** attempt))  # Exponential backoff
        
        return {'paid': False}
    
    async def _handle_needs_username(self, order_data: Dict, chat_id: int):
        """Handle case when username is missing or invalid"""
        order_id = order_data['order_id']
        db.update_order_status(order_id, OrderStatus.NEEDS_USERNAME)
        
        if chat_id:
            message = self.message_templates.needs_username(order_data)
            await self.notification_service.notify_user(chat_id, message)
    
    async def _handle_waiting_payment(self, order_data: Dict, chat_id: int):
        """Handle waiting payment status"""
        order_id = order_data['order_id']
        db.update_order_status(order_id, OrderStatus.WAITING_PAYMENT)
        
        if chat_id:
            message = self.message_templates.waiting_payment(order_data)
            await self.notification_service.notify_user(chat_id, message)
    
    async def _handle_needs_balance(self, order_data: Dict, balance: Dict, chat_id: int):
        """Handle insufficient balance"""
        order_id = order_data['order_id']
        db.update_order_status(order_id, OrderStatus.NEEDS_BALANCE)
        
        # Notify user
        if chat_id:
            message = self.message_templates.needs_balance(order_data)
            await self.notification_service.notify_user(chat_id, message)
        
        # Notify admin
        admin_message = f"⚠️ Недостаточно баланса для заказа {order_id}\n"
        admin_message += f"Нужно: {order_data['stars_amount_total']} ⭐\n"
        admin_message += f"Доступно: {balance['stars_balance']} ⭐"
        await self.notification_service.notify_admin(admin_message)
    
    async def _process_fulfillment(self, order_data: Dict, chat_id: int):
        """Process stars fulfillment"""
        order_id = order_data['order_id']
        to_username = utils.normalize_username(order_data['attached_telegram_username'])
        stars_total = order_data['stars_amount_total']
        
        # Check if already fulfilled
        existing_fulfillment = db.get_fulfillment_by_order(order_id)
        if existing_fulfillment and existing_fulfillment['status'] == FulfillmentStatus.SUCCESS:
            if chat_id:
                message = self.message_templates.fulfillment_success(order_data, existing_fulfillment)
                await self.notification_service.notify_user(chat_id, message)
            return
        
        # Update order status
        db.update_order_status(order_id, OrderStatus.FULFILLING)
        
        # Create fulfillment record
        fulfillment_record = {
            'order_id': order_id,
            'to_username': to_username,
            'stars_total': stars_total,
            'batches': [],
            'status': FulfillmentStatus.PENDING,
            'created_at': utils.now(),
            'updated_at': utils.now(),
            'notes': 'auto-fulfilled'
        }
        
        fulfillment_id = db.create_fulfillment(fulfillment_record)
        
        # Split into batches if needed
        batches = utils.split_stars_into_batches(stars_total, FRAGMENT_MAX)
        successful_batches = []
        failed_batches = []
        
        for i, batch_amount in enumerate(batches):
            try:
                # Generate idempotency key
                idempotency_key = utils.generate_idempotency_key(order_id, to_username, batch_amount)
                
                # Transfer stars
                result = await self._transfer_stars_with_retry(to_username, batch_amount, idempotency_key)
                
                if result['ok']:
                    successful_batches.append({
                        'amount': batch_amount,
                        'transfer_id': result['transfer_id'],
                        'status': 'ok'
                    })
                else:
                    failed_batches.append({
                        'amount': batch_amount,
                        'error': result.get('error_message', 'Unknown error'),
                        'status': 'failed'
                    })
                
                # Small delay between batches
                if i < len(batches) - 1:
                    await utils.sleep(1000)
                    
            except Exception as e:
                failed_batches.append({
                    'amount': batch_amount,
                    'error': str(e),
                    'status': 'failed'
                })
        
        # Update fulfillment status
        all_batches = successful_batches + failed_batches
        total_sent = sum(batch['amount'] for batch in successful_batches)
        
        if failed_batches:
            if successful_batches:
                # Partial fulfillment
                status = FulfillmentStatus.PARTIAL
                notes = f"Partial: {total_sent}/{stars_total} sent"
                await self._handle_partial_fulfillment(order_data, total_sent, stars_total - total_sent, chat_id)
            else:
                # Complete failure
                status = FulfillmentStatus.FAILED
                notes = f"Failed: {', '.join([b['error'] for b in failed_batches])}"
                await self._handle_fulfillment_failure(order_data, failed_batches, chat_id)
        else:
            # Complete success
            status = FulfillmentStatus.SUCCESS
            notes = f"Success: {total_sent} sent"
            db.update_order_status(order_id, OrderStatus.FULFILLED)
            await self._handle_fulfillment_success(order_data, chat_id)
        
        # Update fulfillment record
        db.update_fulfillment_status(fulfillment_id, status, {
            'batches': all_batches,
            'notes': notes
        })
    
    async def _transfer_stars_with_retry(self, to_username: str, stars_amount: int, idempotency_key: str) -> Dict:
        """Transfer stars with retry logic"""
        for attempt in range(MAX_RETRY):
            try:
                result = await fragment.transfer_stars(to_username, stars_amount, idempotency_key)
                
                if result['ok']:
                    return result
                
                # Check for rate limiting
                if result.get('error_code') in ['rate_limited', 'daily_limit_exceeded']:
                    wait_time = 1000 * (2 ** attempt)  # Exponential backoff
                    await utils.sleep(wait_time)
                    continue
                
                # For other errors, return immediately
                return result
                
            except Exception as e:
                if attempt == MAX_RETRY - 1:
                    return {
                        'ok': False,
                        'error_message': str(e)
                    }
                wait_time = 1000 * (2 ** attempt)
                await utils.sleep(wait_time)
        
        return {'ok': False, 'error_message': 'Max retries exceeded'}
    
    async def _handle_fulfillment_success(self, order_data: Dict, chat_id: int):
        """Handle successful fulfillment"""
        if chat_id:
            message = self.message_templates.fulfillment_success(order_data)
            await self.notification_service.notify_user(chat_id, message)
        
        # Логирование выполненного заказа
        fulfillment_data = db.get_fulfillment_by_order(order_data['order_id'])
        if fulfillment_data:
            await self.order_logger.log_order_completion(order_data, fulfillment_data)
    
    async def _handle_partial_fulfillment(self, order_data: Dict, sent: int, left: int, chat_id: int):
        """Handle partial fulfillment"""
        order_id = order_data['order_id']
        db.update_order_status(order_id, OrderStatus.PARTIALLY_FULFILLED)
        
        if chat_id:
            message = self.message_templates.partial_fulfillment(order_data, sent, left)
            await self.notification_service.notify_user(chat_id, message)
        
        # Notify admin
        admin_message = f"⚠️ Частичная выдача заказа {order_id}\n"
        admin_message += f"Отправлено: {sent} ⭐\n"
        admin_message += f"Осталось: {left} ⭐"
        await self.notification_service.notify_admin(admin_message)
    
    async def _handle_fulfillment_failure(self, order_data: Dict, failed_batches: List[Dict], chat_id: int):
        """Handle fulfillment failure"""
        order_id = order_data['order_id']
        db.update_order_status(order_id, OrderStatus.FAILED)
        
        if chat_id:
            error_message = ', '.join([b['error'] for b in failed_batches])
            message = self.message_templates.fulfillment_failure(order_data, error_message)
            await self.notification_service.notify_user(chat_id, message)
        
        # Notify admin
        admin_message = f"❌ Ошибка выдачи заказа {order_id}\n"
        admin_message += f"Ошибки: {', '.join([b['error'] for b in failed_batches])}"
        await self.notification_service.notify_admin(admin_message)
    
    async def _handle_error(self, order_id: str, error_message: str, chat_id: int):
        """Handle general errors"""
        print(f"Error processing order {order_id}: {error_message}")
        
        # Логирование ошибки
        self.order_logger.log_error(error_message, order_id)
        
        if chat_id:
            message = f"❌ Произошла ошибка при обработке заказа {order_id}:\n{error_message}"
            await self.notification_service.notify_user(chat_id, message)
        
        # Notify admin
        admin_message = f"❌ Ошибка обработки заказа {order_id}:\n{error_message}"
        await self.notification_service.notify_admin(admin_message)
    
    async def check_pending_orders(self):
        """Check and process pending orders"""
        # This would be called periodically to check for new orders
        # Implementation depends on how you receive order notifications
        pass
    
    async def remind_unpaid_orders(self):
        """Send reminders for unpaid orders"""
        # Implementation for sending payment reminders
        pass
