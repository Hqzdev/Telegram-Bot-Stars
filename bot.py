import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from typing import Dict, List

from config import TELEGRAM_TOKEN, ADMIN_IDS, OrderStatus
from database import db
from integrations import funpay, fragment, utils, NotificationService
from order_processor import OrderProcessor
from message_templates import MessageTemplates

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramStarsBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        self.notification_service = NotificationService(self.application.bot)
        self.order_processor = OrderProcessor(self.notification_service)
        self.message_templates = MessageTemplates()
        
        # Initialize logging system
        from logging_system import OrderLogger
        self.order_logger = OrderLogger(self.notification_service)
        
        # User states for username confirmation
        self.user_states = {}  # {user_id: {'state': 'waiting_username', 'order_id': '...'}}
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup command and message handlers"""
        
        # User commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("price", self.price_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("terms", self.terms_command))
        self.application.add_handler(CommandHandler("order", self.order_command))
        
        # Admin commands
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        
        # Message handler for username input
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            self.message_templates.start_message(),
            parse_mode='HTML'
        )
    
    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /price command"""
        try:
            offers = await funpay.list_offers()
            db.save_offers(offers)  # Cache offers
            
            message = self.message_templates.price_message(offers)
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error in price command: {e}")
            await update.message.reply_text("❌ Ошибка загрузки цен. Попробуйте позже.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await update.message.reply_text(
            self.message_templates.help_message(),
            parse_mode='HTML'
        )
    
    async def terms_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /terms command"""
        await update.message.reply_text(
            self.message_templates.terms_message(),
            parse_mode='HTML'
        )
    
    async def order_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /order command"""
        if not context.args:
            await update.message.reply_text(
                "❌ Укажите ID заказа: /order <ID>"
            )
            return
        
        order_id = context.args[0]
        user_id = update.effective_user.id
        
        try:
            # Get order from database first
            order_data = db.get_order(order_id)
            
            if not order_data:
                # Try to get from FunPay
                order_data = await funpay.get_order(order_id)
                if order_data:
                    db.save_order(order_data)
            
            if not order_data:
                await update.message.reply_text(f"❌ Заказ №{order_id} не найден.")
                return
            
            # Get fulfillment data
            fulfillment_data = db.get_fulfillment_by_order(order_id)
            
            message = self.message_templates.order_status(order_data, fulfillment_data)
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error in order command: {e}")
            await update.message.reply_text("❌ Ошибка получения статуса заказа.")
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin commands"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Доступ запрещён.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "🔧 <b>Админ команды:</b>\n\n"
                "/admin orders [N] — последние заказы\n"
                "/admin fulfill [ID] — принудительная выдача\n"
                "/admin balance — баланс Fragment\n"
                "/admin offers — список офферов\n"
                "/admin ping — статус сервисов\n\n"
                "📊 <b>Статистика:</b>\n"
                "/stats — статистика за текущий месяц\n"
                "/stats month [YYYY-MM] — статистика за месяц\n"
                "/stats all — общая статистика\n"
                "/stats recent [N] — последние заказы",
                parse_mode='HTML'
            )
            return
        
        subcommand = context.args[0].lower()
        
        try:
            if subcommand == "orders":
                await self._handle_admin_orders(update, context)
            elif subcommand == "fulfill":
                await self._handle_admin_fulfill(update, context)
            elif subcommand == "balance":
                await self._handle_admin_balance(update, context)
            elif subcommand == "offers":
                await self._handle_admin_offers(update, context)
            elif subcommand == "ping":
                await self._handle_admin_ping(update, context)
            else:
                await update.message.reply_text("❌ Неизвестная команда.")
                
        except Exception as e:
            logger.error(f"Error in admin command {subcommand}: {e}")
            await update.message.reply_text(f"❌ Ошибка выполнения команды: {e}")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle stats command"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ Доступ запрещён.")
            return
        
        if not context.args:
            # Показать статистику за текущий месяц
            await self._handle_stats_current_month(update, context)
            return
        
        subcommand = context.args[0].lower()
        
        try:
            if subcommand == "month":
                await self._handle_stats_month(update, context)
            elif subcommand == "all":
                await self._handle_stats_all_time(update, context)
            elif subcommand == "recent":
                await self._handle_stats_recent(update, context)
            else:
                await update.message.reply_text(
                    "📊 <b>Команды статистики:</b>\n\n"
                    "/stats — статистика за текущий месяц\n"
                    "/stats month [YYYY-MM] — статистика за конкретный месяц\n"
                    "/stats all — общая статистика за всё время\n"
                    "/stats recent [N] — последние N заказов",
                    parse_mode='HTML'
                )
                
        except Exception as e:
            logger.error(f"Error in stats command {subcommand}: {e}")
            await update.message.reply_text(f"❌ Ошибка получения статистики: {e}")
                
        except Exception as e:
            logger.error(f"Error in admin command {subcommand}: {e}")
            await update.message.reply_text(f"❌ Ошибка выполнения команды: {e}")
    
    async def _handle_admin_orders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin orders command"""
        limit = 10
        if len(context.args) > 1:
            try:
                limit = int(context.args[1])
                limit = min(limit, 50)  # Max 50 orders
            except ValueError:
                pass
        
        orders = db.get_recent_orders(limit)
        message = self.message_templates.admin_orders_list(orders)
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def _handle_admin_fulfill(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin fulfill command"""
        if len(context.args) < 2:
            await update.message.reply_text("❌ Укажите ID заказа: /admin fulfill <ID>")
            return
        
        order_id = context.args[1]
        
        # Process order
        await self.order_processor.process_order(order_id)
        await update.message.reply_text(f"✅ Заказ {order_id} отправлен на обработку.")
    
    async def _handle_admin_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin balance command"""
        balance = await fragment.get_balance()
        message = self.message_templates.admin_balance(balance)
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def _handle_admin_offers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin offers command"""
        offers = await funpay.list_offers()
        db.save_offers(offers)
        
        message = "📦 <b>Офферы из FunPay:</b>\n\n"
        for offer in offers:
            status = "✅ Активен" if offer['is_active'] else "❌ Неактивен"
            message += f"<b>{offer['title']}</b> ({status})\n"
            message += f"ID: {offer['offer_id']}\n"
            message += f"⭐ {offer['stars_amount']:,} | 💰 {offer['price']} {offer['currency']}\n\n"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def _handle_admin_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin ping command"""
        services_status = {}
        
        # Check FunPay
        try:
            await funpay.list_offers()
            services_status['FunPay'] = {'ok': True}
        except Exception as e:
            services_status['FunPay'] = {'ok': False, 'error': str(e)}
        
        # Check Fragment
        try:
            await fragment.get_balance()
            services_status['Fragment'] = {'ok': True}
        except Exception as e:
            services_status['Fragment'] = {'ok': False, 'error': str(e)}
        
        # Check Database
        try:
            db.get_recent_orders(1)
            services_status['Database'] = {'ok': True}
        except Exception as e:
            services_status['Database'] = {'ok': False, 'error': str(e)}
        
        message = self.message_templates.admin_ping(services_status)
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def _handle_stats_current_month(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle current month statistics"""
        from datetime import datetime
        
        stats = await self.order_processor.order_logger.get_monthly_statistics()
        
        month_name = datetime.now().strftime('%B %Y')
        avg_check = stats['total_revenue'] / stats['total_orders'] if stats['total_orders'] > 0 else 0
        
        message = f"""📊 <b>Статистика за {month_name}</b>

📦 <b>Заказы:</b>
• Выполнено заказов: {stats['total_orders']}
• Продано звёзд: {stats['total_stars']:,} ⭐

💰 <b>Доход:</b>
• Общий доход: {stats['total_revenue']:,.2f} ₽
• Средний чек: {avg_check:,.2f} ₽"""

        await update.message.reply_text(message, parse_mode='HTML')
    
    async def _handle_stats_month(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle specific month statistics"""
        if len(context.args) < 2:
            await update.message.reply_text("❌ Укажите месяц: /stats month YYYY-MM")
            return
        
        try:
            date_str = context.args[1]
            year, month = map(int, date_str.split('-'))
            
            stats = await self.order_processor.order_logger.get_monthly_statistics(year, month)
            
            from datetime import datetime
            month_name = datetime(year, month, 1).strftime('%B %Y')
            avg_check = stats['total_revenue'] / stats['total_orders'] if stats['total_orders'] > 0 else 0
            
            message = f"""📊 <b>Статистика за {month_name}</b>

📦 <b>Заказы:</b>
• Выполнено заказов: {stats['total_orders']}
• Продано звёзд: {stats['total_stars']:,} ⭐

💰 <b>Доход:</b>
• Общий доход: {stats['total_revenue']:,.2f} ₽
• Средний чек: {avg_check:,.2f} ₽"""

            await update.message.reply_text(message, parse_mode='HTML')
            
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Неверный формат даты. Используйте: YYYY-MM")
    
    async def _handle_stats_all_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all-time statistics"""
        stats = await self.order_processor.order_logger.get_all_time_statistics()
        avg_check = stats['total_revenue'] / stats['total_orders'] if stats['total_orders'] > 0 else 0
        
        message = f"""📊 <b>Общая статистика за всё время</b>

📦 <b>Заказы:</b>
• Выполнено заказов: {stats['total_orders']}
• Продано звёзд: {stats['total_stars']:,} ⭐

💰 <b>Доход:</b>
• Общий доход: {stats['total_revenue']:,.2f} ₽
• Средний чек: {avg_check:,.2f} ₽"""

        await update.message.reply_text(message, parse_mode='HTML')
    
    async def _handle_stats_recent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle recent orders statistics"""
        limit = 10
        if len(context.args) > 1:
            try:
                limit = int(context.args[1])
                limit = min(limit, 50)  # Максимум 50 заказов
            except ValueError:
                pass
        
        recent_orders = self.order_processor.order_logger.get_recent_orders(limit)
        
        if not recent_orders:
            await update.message.reply_text("📋 Последних заказов не найдено.")
            return
        
        message = f"📋 <b>Последние {len(recent_orders)} заказов:</b>\n\n"
        
        for order in recent_orders:
            # Форматирование даты
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(order['timestamp'].replace('Z', '+00:00'))
                formatted_date = dt.strftime('%d.%m.%Y %H:%M')
            except:
                formatted_date = order['timestamp'][:16]
            
            message += f"📦 <b>№{order['order_id']}</b> ({formatted_date})\n"
            message += f"   ⭐ {order['stars_amount']:,} | 💰 {order['price_rub']:,.2f} ₽\n"
            message += f"   👤 {order['buyer_username']} → {order['to_username']}\n\n"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (mainly for username input)"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        # Check if user is in waiting state
        if user_id in self.user_states:
            state = self.user_states[user_id]
            
            if state['state'] == 'waiting_username':
                await self._handle_username_input(update, text, state['order_id'])
                return
        
        # Check if message looks like an order ID
        if self._looks_like_order_id(text):
            await self.order_command(update, context)
            return
        
        # Default response
        await update.message.reply_text(
            "💡 Используйте команды:\n"
            "/start — начало работы\n"
            "/price — цены\n"
            "/help — инструкции\n"
            "/order <ID> — статус заказа"
        )
    
    async def _handle_username_input(self, update: Update, text: str, order_id: str):
        """Handle username input from user"""
        user_id = update.effective_user.id
        
        # Validate username
        if not utils.validate_username(text):
            await update.message.reply_text(
                "❌ Неверный формат @юзернейма.\n"
                "Пример: @example или example\n"
                "Должно быть 5-32 символа, только буквы, цифры и подчёркивания."
            )
            return
        
        # Normalize username
        normalized_username = utils.normalize_username(text)
        
        # Get order data
        order_data = db.get_order(order_id)
        if not order_data:
            await update.message.reply_text("❌ Заказ не найден.")
            del self.user_states[user_id]
            return
        
        # Confirm username
        message = self.message_templates.confirm_username(order_data, normalized_username)
        await update.message.reply_text(message, parse_mode='HTML')
        
        # Update state to waiting confirmation
        self.user_states[user_id] = {
            'state': 'confirming_username',
            'order_id': order_id,
            'username': normalized_username
        }
    
    def _looks_like_order_id(self, text: str) -> bool:
        """Check if text looks like an order ID"""
        # Simple heuristic - order IDs are usually alphanumeric and 8-20 chars
        if len(text) < 8 or len(text) > 20:
            return False
        
        # Check if contains only alphanumeric characters and common separators
        import re
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', text))
    
    async def process_order_webhook(self, order_id: str, chat_id: int = None):
        """Process order from webhook (external call)"""
        await self.order_processor.process_order(order_id, chat_id)
    
    async def start(self):
        """Start the bot"""
        logger.info("Starting Telegram Stars Bot...")
        
        # Initialize database
        db.init_database()
        
        # Setup logging
        self.order_logger.setup_logging()
        
        logger.info("Bot started successfully!")
        
        # Keep the bot running
        await self.application.run_polling()

# Global bot instance
bot_instance = None

async def main():
    """Main function"""
    global bot_instance
    bot_instance = TelegramStarsBot()
    await bot_instance.start()

if __name__ == '__main__':
    asyncio.run(main())
