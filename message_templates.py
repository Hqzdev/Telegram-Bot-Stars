from config import CURRENCY, PAYMENT_WAIT_MINUTES, AUTO_CLOSE_MIN, FRAGMENT_MIN, FRAGMENT_MAX
from integrations import utils

class MessageTemplates:
    def start_message(self) -> str:
        """Welcome message"""
        return f"""Привет! Я помогу купить и доставить Telegram Stars.

1️⃣ Выберите оффер (количество звёзд) на FunPay
2️⃣ Укажите в заказе ваш Telegram @юзернейм — на него придут звёзды
3️⃣ Оплатите заказ

Я автоматически проверю оплату и отправлю звёзды через Fragment.

Команды:
/price — цены и пакеты
/help — инструкции
/terms — условия покупки"""

    def price_message(self, offers: list) -> str:
        """Price list message"""
        if not offers:
            return "❌ Офферы временно недоступны. Попробуйте позже."
        
        message = f"<b>Актуальные офферы:</b>\n\n"
        
        for offer in offers:
            if offer['is_active']:
                message += f"📦 <b>{offer['title']}</b>\n"
                message += f"   ⭐ {offer['stars_amount']:,} звёзд\n"
                message += f"   💰 {offer['price']} {offer['currency']}\n\n"
        
        message += f"<b>Валюта:</b> {CURRENCY}\n"
        message += "Комиссии уже учтены в цене."
        
        return message

    def waiting_payment(self, order_data: dict) -> str:
        """Waiting payment message"""
        order_id = order_data['order_id']
        stars_total = order_data['stars_amount_total']
        
        return f"""📋 <b>Заказ №{order_id}</b> на {stars_total:,} ⭐ создан

Статус: <b>ожидает оплаты</b>

Пожалуйста, завершите оплату на FunPay.
Я проверю и выдам звёзды автоматически.

⏰ Заказ будет автоматически закрыт через {AUTO_CLOSE_MIN} минут, если оплата не поступит."""

    def needs_username(self, order_data: dict) -> str:
        """Needs username message"""
        order_id = order_data['order_id']
        
        return f"""❓ В заказе №{order_id} не найден корректный @юзернейм для доставки.

Пожалуйста, отправьте сюда ваш Telegram @юзернейм (например, @example).

⚠️ <b>Важно:</b> Убедитесь, что у вас включены личные сообщения от незнакомых пользователей."""

    def confirm_username(self, order_data: dict, username: str) -> str:
        """Confirm username message"""
        stars_total = order_data['stars_amount_total']
        normalized_username = utils.normalize_username(username)
        
        return f"""✅ Подтвердите: отправить {stars_total:,} ⭐ на {normalized_username}?

Напишите «Да», если всё верно, или пришлите правильный @юзернейм."""

    def needs_balance(self, order_data: dict) -> str:
        """Needs balance message"""
        order_id = order_data['order_id']
        stars_total = order_data['stars_amount_total']
        
        return f"""✅ Заказ №{order_id} оплачен!

Мы пополняем баланс для выдачи {stars_total:,} ⭐.
Как только Stars будут отправлены — пришлю чек.

Спасибо за терпение! 🙏"""

    def fulfillment_success(self, order_data: dict, fulfillment_data: dict = None) -> str:
        """Successful fulfillment message"""
        order_id = order_data['order_id']
        stars_total = order_data['stars_amount_total']
        to_username = utils.normalize_username(order_data['attached_telegram_username'])
        
        message = f"""🎉 <b>Готово!</b>

Заказ №{order_id}: отправлено {stars_total:,} ⭐ на {to_username} через Fragment.

Спасибо за покупку! 

💡 Если потребуется чек/скрин перевода — напишите."""

        if fulfillment_data and fulfillment_data.get('batches'):
            batches = fulfillment_data['batches']
            if len(batches) > 1:
                message += f"\n\n📊 <b>Детали выдачи:</b>\n"
                for i, batch in enumerate(batches, 1):
                    if batch['status'] == 'ok':
                        transfer_id = utils.mask_transaction_id(batch.get('transfer_id', ''))
                        message += f"   {i}. {batch['amount']:,} ⭐ (ID: {transfer_id})\n"
        
        return message

    def partial_fulfillment(self, order_data: dict, sent: int, left: int) -> str:
        """Partial fulfillment message"""
        order_id = order_data['order_id']
        
        return f"""⚠️ <b>Обновление по заказу №{order_id}:</b>

✅ Отправлено: {sent:,} ⭐
⏳ Осталось: {left:,} ⭐

Доставим оставшуюся часть в ближайшее время.
Спасибо за терпение! 🙏"""

    def fulfillment_failure(self, order_data: dict, error_message: str) -> str:
        """Fulfillment failure message"""
        order_id = order_data['order_id']
        
        return f"""❌ Не удалось отправить Stars по заказу №{order_id}

Ошибка: {error_message}

Мы уже разбираемся. Либо повторим попытку, либо вернём средства — как вам удобнее.

Свяжитесь с поддержкой для решения вопроса."""

    def payment_reminder(self, order_data: dict) -> str:
        """Payment reminder message"""
        order_id = order_data['order_id']
        stars_total = order_data['stars_amount_total']
        
        return f"""⏰ <b>Напоминание:</b> заказ №{order_id} на {stars_total:,} ⭐ всё ещё ожидает оплаты на FunPay.

Если передумали — ничего делать не нужно, заказ сам закроется через {AUTO_CLOSE_MIN} минут."""

    def help_message(self) -> str:
        """Help message"""
        return f"""📖 <b>Как оформить заказ:</b>

1️⃣ Перейдите на FunPay и выберите нужный оффер
2️⃣ В поле "Комментарий к заказу" укажите ваш Telegram @юзернейм
3️⃣ Оплатите заказ любым удобным способом
4️⃣ Я автоматически проверю оплату и отправлю звёзды

<b>Важные моменты:</b>
• Убедитесь, что @юзернейм указан правильно
• Включите личные сообщения от незнакомых
• Время выдачи: до 5 минут после оплаты
• Минимальная выдача: {FRAGMENT_MIN:,} ⭐
• Максимальная за раз: {FRAGMENT_MAX:,} ⭐

<b>Команды:</b>
/price — посмотреть цены
/order [ID] — статус заказа
/terms — условия покупки"""

    def terms_message(self) -> str:
        """Terms and conditions message"""
        return f"""📋 <b>Условия покупки Telegram Stars:</b>

<b>Цены и оплата:</b>
• Цены указаны в {CURRENCY}
• Комиссии уже учтены в стоимости
• Оплата через FunPay (карты, электронные кошельки)

<b>Доставка:</b>
• Автоматическая отправка через Fragment
• Время доставки: до 5 минут после оплаты
• Минимальная выдача: {FRAGMENT_MIN:,} ⭐
• Максимальная за раз: {FRAGMENT_MAX:,} ⭐

<b>Возврат и отмена:</b>
• Возврат средств при технических проблемах
• Отмена заказа до оплаты — бесплатно
• После отправки звёзд — возврат невозможен

<b>Ограничения:</b>
• Один заказ на один @юзернейм
• Заказы без указания @юзернейма не обрабатываются
• Автоматическое закрытие неоплаченных заказов через {AUTO_CLOSE_MIN} минут

<b>Поддержка:</b>
• По всем вопросам обращайтесь к администратору
• Время ответа: до 24 часов"""

    def order_status(self, order_data: dict, fulfillment_data: dict = None) -> str:
        """Order status message"""
        order_id = order_data['order_id']
        status = order_data['status']
        stars_total = order_data['stars_amount_total']
        created_at = order_data['created_at']
        
        # Format date
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            formatted_date = dt.strftime('%d.%m.%Y %H:%M')
        except:
            formatted_date = created_at
        
        message = f"""📋 <b>Заказ №{order_id}</b>

📅 Создан: {formatted_date}
⭐ Количество: {stars_total:,} звёзд
💰 Сумма: {order_data['total_price']} {order_data['currency']}
📊 Статус: <b>{self._format_status(status)}</b>"""

        if order_data.get('attached_telegram_username'):
            username = utils.normalize_username(order_data['attached_telegram_username'])
            message += f"\n👤 Получатель: {username}"

        if fulfillment_data:
            fulfillment_status = fulfillment_data['status']
            message += f"\n🚀 Выдача: <b>{self._format_fulfillment_status(fulfillment_status)}</b>"
            
            if fulfillment_data.get('batches'):
                batches = fulfillment_data['batches']
                successful = sum(1 for b in batches if b['status'] == 'ok')
                total = len(batches)
                message += f"\n📊 Прогресс: {successful}/{total} батчей"

        return message

    def admin_orders_list(self, orders: list) -> str:
        """Admin orders list message"""
        if not orders:
            return "📋 Заказов не найдено."
        
        message = f"📋 <b>Последние {len(orders)} заказов:</b>\n\n"
        
        for order in orders:
            status_emoji = self._get_status_emoji(order['status'])
            message += f"{status_emoji} <b>№{order['order_id']}</b>\n"
            message += f"   ⭐ {order['stars_amount_total']:,} | "
            message += f"💰 {order['total_price']} {order['currency']}\n"
            message += f"   👤 {order['buyer_username']} | "
            message += f"📊 {order['status']}\n"
            message += f"   📅 {order['created_at'][:16]}\n\n"
        
        return message

    def admin_balance(self, balance: dict) -> str:
        """Admin balance message"""
        return f"""💰 <b>Баланс Fragment:</b>

⭐ Звёзд: {balance['stars_balance']:,}
📊 Дневной лимит: {balance['daily_limit_left']:,}"""

    def admin_ping(self, services_status: dict) -> str:
        """Admin ping message"""
        message = "🏓 <b>Статус сервисов:</b>\n\n"
        
        for service, status in services_status.items():
            emoji = "✅" if status['ok'] else "❌"
            message += f"{emoji} <b>{service}:</b> "
            message += f"{'OK' if status['ok'] else 'ERROR'}"
            if not status['ok'] and status.get('error'):
                message += f" ({status['error']})"
            message += "\n"
        
        return message

    def _format_status(self, status: str) -> str:
        """Format order status for display"""
        status_map = {
            'NEW': '🆕 Новый',
            'WAITING_PAYMENT': '⏳ Ожидает оплаты',
            'PAID': '✅ Оплачен',
            'FULFILLING': '🚀 Выполняется',
            'FULFILLED': '🎉 Выполнен',
            'NEEDS_USERNAME': '❓ Нужен юзернейм',
            'NEEDS_BALANCE': '💰 Ожидает пополнения',
            'FAILED': '❌ Ошибка',
            'PARTIALLY_FULFILLED': '⚠️ Частично выполнен'
        }
        return status_map.get(status, status)

    def _format_fulfillment_status(self, status: str) -> str:
        """Format fulfillment status for display"""
        status_map = {
            'PENDING': '⏳ В ожидании',
            'SUCCESS': '✅ Успешно',
            'FAILED': '❌ Ошибка',
            'PARTIAL': '⚠️ Частично'
        }
        return status_map.get(status, status)

    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for status"""
        emoji_map = {
            'NEW': '🆕',
            'WAITING_PAYMENT': '⏳',
            'PAID': '✅',
            'FULFILLING': '🚀',
            'FULFILLED': '🎉',
            'NEEDS_USERNAME': '❓',
            'NEEDS_BALANCE': '💰',
            'FAILED': '❌',
            'PARTIALLY_FULFILLED': '⚠️'
        }
        return emoji_map.get(status, '📋')
