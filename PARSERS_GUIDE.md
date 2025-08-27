# 🔍 Руководство по парсерам FunPay и Fragment

## 📋 Обзор

Поскольку FunPay и Fragment не предоставляют публичные API, мы используем парсеры для автоматизации работы с этими платформами через веб-интерфейс.

## 🏗️ Архитектура парсеров

### FunPay Parser (`funpay_parser.py`)
- **Авторизация** через логин/пароль
- **Получение заказов** со страницы заказов
- **Проверка оплаты** по статусу заказа
- **Отправка сообщений** в чат заказа
- **Парсинг данных** заказов (цена, количество звёзд, Telegram username)

### Fragment Parser (`fragment_parser.py`)
- **Авторизация** через номер телефона
- **Получение баланса** Stars
- **Отправка Stars** пользователям
- **Обработка ошибок** и лимитов

## ⚙️ Настройка

### 1. Установка зависимостей
```bash
pip install selenium beautifulsoup4 requests webdriver-manager undetected-chromedriver
```

### 2. Настройка переменных окружения
Создайте файл `.env` на основе `env_example.txt`:

```env
# FunPay Parser Configuration
FUNPAY_LOGIN=your_funpay_login_here
FUNPAY_PASSWORD=your_funpay_password_here

# Fragment Parser Configuration  
FRAGMENT_PHONE=+1234567890

# Parser Settings
USE_MOCK_PARSERS=false
BROWSER_HEADLESS=true
```

### 3. Режимы работы

#### Mock режим (для разработки)
```env
USE_MOCK_PARSERS=true
```
- Использует mock данные
- Не требует реальных аккаунтов
- Подходит для тестирования

#### Реальный режим (для продакшена)
```env
USE_MOCK_PARSERS=false
```
- Использует реальные парсеры
- Требует валидные аккаунты
- Автоматизирует реальные операции

## 🔧 Использование

### Инициализация парсеров
```python
from integrations import FunPayAPI, FragmentAPI

# Автоматически выбирает mock или реальный парсер
funpay_api = FunPayAPI()
fragment_api = FragmentAPI()
```

### Получение заказов FunPay
```python
# Получение списка офферов/заказов
offers = await funpay_api.list_offers()

# Получение деталей конкретного заказа
order = await funpay_api.get_order("order_id")

# Проверка оплаты
payment = await funpay_api.verify_payment("order_id")
```

### Работа с Fragment
```python
# Получение баланса
balance = await fragment_api.get_balance()

# Отправка Stars
result = await fragment_api.transfer_stars(
    to_username="@user",
    stars_amount=100,
    idempotency_key="unique_key"
)
```

## 🧪 Тестирование

### Запуск тестов парсеров
```bash
python3 test_parsers.py
```

### Запуск основных тестов
```bash
python3 test_bot.py
```

### Тестирование workflow
```bash
python3 test_logging.py
```

## 🔍 Детали реализации

### FunPay Parser

#### Селекторы элементов
```python
selectors = {
    'login_form': 'form[action="/account/login/"]',
    'login_input': 'input[name="login"]',
    'password_input': 'input[name="password"]',
    'orders_link': 'a[href*="/orders/"]',
    'order_item': '.order-item',
    'order_status': '.order-status',
    'order_amount': '.order-amount',
    'chat_messages': '.chat-message'
}
```

#### Парсинг заказов
- Извлечение ID заказа
- Парсинг статуса оплаты
- Извлечение Telegram username из описания
- Конвертация валют в рубли

#### Обработка ошибок
- Retry логика с экспоненциальной задержкой
- Обработка rate limiting
- Fallback на mock данные при ошибках

### Fragment Parser

#### Процесс авторизации
1. Переход на Fragment.com
2. Ввод номера телефона
3. Ожидание ввода кода (ручной ввод)
4. Проверка успешной авторизации

#### Отправка Stars
1. Переход на страницу отправки
2. Ввод получателя (без @)
3. Ввод количества Stars
4. Подтверждение отправки
5. Проверка результата

## 🛡️ Безопасность

### Защита от обнаружения
- Использование `undetected-chromedriver`
- Рандомизация User-Agent
- Отключение автоматических уведомлений
- Эмуляция человеческого поведения

### Обработка ошибок
- Автоматические повторы при сбоях
- Логирование всех операций
- Graceful degradation на mock данные
- Уведомления администраторов

## 📊 Мониторинг

### Логирование
```python
# Логи парсеров
2025-08-20 20:06:22 - telegram_stars_bot - INFO - Order completed: {...}
2025-08-20 20:06:23 - telegram_stars_bot - ERROR - Error occurred: {...}
```

### Метрики
- Количество успешных операций
- Время выполнения запросов
- Частота ошибок
- Статус авторизации

## 🔄 Обновления и поддержка

### Адаптация к изменениям сайтов
Парсеры могут потребовать обновления при изменении структуры сайтов:

1. **Обновление селекторов** в `selectors` словарях
2. **Добавление новых паттернов** парсинга
3. **Тестирование** на актуальных данных
4. **Обновление mock данных** для совместимости

### Резервные стратегии
- Fallback на mock данные
- Ручная обработка критических заказов
- Уведомления администраторов о проблемах
- Автоматическое переключение режимов

## 🚨 Устранение неполадок

### Частые проблемы

#### Ошибки авторизации
```bash
# Проверьте правильность данных
FUNPAY_LOGIN=your_actual_login
FUNPAY_PASSWORD=your_actual_password
FRAGMENT_PHONE=+your_actual_phone
```

#### Проблемы с браузером
```bash
# Установите Chrome/Chromium
# Обновите webdriver-manager
pip install --upgrade webdriver-manager
```

#### Ошибки парсинга
```bash
# Включите mock режим для тестирования
USE_MOCK_PARSERS=true
```

### Отладка
```python
# Включение подробных логов
import logging
logging.basicConfig(level=logging.DEBUG)

# Проверка статуса парсеров
print(f"FunPay logged in: {funpay_api.parser.is_logged_in}")
print(f"Fragment logged in: {fragment_api.parser.is_logged_in}")
```

## 📈 Производительность

### Оптимизации
- Headless режим браузера
- Отключение изображений
- Кэширование сессий
- Параллельная обработка

### Лимиты
- Задержки между запросами
- Ограничения на количество операций
- Rate limiting для API вызовов
- Таймауты для операций

---

**Версия:** 1.0.0  
**Статус:** Готово к использованию  
**Последнее обновление:** 2024
