# 🤖 Telegram Stars Bot

Автоматизированный бот для продажи Telegram Stars через FunPay с мгновенной доставкой через Fragment.

## 🎯 Возможности

- **Автоматическая обработка заказов** с FunPay
- **Мгновенная доставка Stars** через Fragment
- **Система логирования** и статистики
- **Парсеры для FunPay и Fragment** (без API)
- **Антифрод защита** и идемпотентность
- **Административная панель** с командами
- **Подробная статистика** по заказам и доходам

## 🏗️ Архитектура

### Основные компоненты
- **`bot.py`** - Telegram бот и обработчики команд
- **`order_processor.py`** - Логика обработки заказов
- **`funpay_parser.py`** - Парсер FunPay для получения заказов
- **`fragment_parser.py`** - Парсер Fragment для отправки Stars
- **`integrations.py`** - API интеграции и парсеры
- **`database.py`** - Работа с SQLite базой данных
- **`logging_system.py`** - Система логирования и статистики
- **`message_templates.py`** - Шаблоны сообщений

### База данных
- **`orders`** - Заказы и их статусы
- **`fulfillments`** - Записи о выдаче Stars
- **`offers`** - Доступные офферы
- **`order_logs`** - Детальные логи выполненных заказов

## ⚙️ Установка и настройка

### 1. Клонирование репозитория
```bash
git clone https://github.com/your-username/Telegram-Bot-Stars.git
cd Telegram-Bot-Stars
```

### 2. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения
Создайте файл `.env` на основе `env_example.txt`:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321

# FunPay Parser Configuration
FUNPAY_LOGIN=your_funpay_login_here
FUNPAY_PASSWORD=your_funpay_password_here

# Fragment Parser Configuration  
FRAGMENT_PHONE=+1234567890

# Parser Settings
USE_MOCK_PARSERS=false
BROWSER_HEADLESS=true

# Business Rules
CURRENCY=RUB
PAYMENT_WAIT_MINUTES=30
REMIND_EACH_MIN=10
AUTO_CLOSE_MIN=120
FRAGMENT_MIN=50
FRAGMENT_MAX=20000
MAX_RETRY=5
MAX_RETRY_VERIFY=5
RETRY_AFTER_MIN=30

# Database Configuration
DATABASE_PATH=bot_database.db
```

### 4. Запуск бота
```bash
python3 run.py
```

## 🔧 Режимы работы

### Mock режим (для разработки)
```env
USE_MOCK_PARSERS=true
```
- Использует тестовые данные
- Не требует реальных аккаунтов
- Подходит для разработки и тестирования

### Реальный режим (для продакшена)
```env
USE_MOCK_PARSERS=false
```
- Использует реальные парсеры
- Требует валидные аккаунты FunPay и Fragment
- Автоматизирует реальные операции

## 📱 Команды пользователя

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и инструкция |
| `/price` | Показать актуальные цены |
| `/order <id>` | Статус заказа |
| `/help` | Справка по использованию |
| `/terms` | Условия использования |

## 👨‍💼 Команды администратора

| Команда | Описание |
|---------|----------|
| `/admin orders <N>` | Последние N заказов |
| `/admin fulfill <order_id>` | Принудительная выдача |
| `/admin balance` | Баланс Fragment |
| `/admin offers` | Список офферов |
| `/admin ping` | Статус сервисов |

### 📊 Команды статистики
| Команда | Описание |
|---------|----------|
| `/stats` | Статистика за текущий месяц |
| `/stats month [YYYY-MM]` | Статистика за конкретный месяц |
| `/stats all` | Общая статистика за всё время |
| `/stats recent [N]` | Последние N заказов |

## 🔄 Машина состояний заказа

```
NEW → WAITING_PAYMENT → PAID → FULFILLING → FULFILLED
  ↓         ↓           ↓         ↓
NEEDS_USERNAME    NEEDS_BALANCE  FAILED
                      ↓
              PARTIALLY_FULFILLED
```

## 🛡️ Безопасность

### Антифрод меры
- **Проверка оплаты** перед выдачей
- **Идемпотентность** для предотвращения дублирования
- **Лимиты повторных попыток**
- **Маскирование транзакционных ID**
- **Валидация Telegram username**

### Парсеры
- **Undetected ChromeDriver** для обхода защиты
- **Экспоненциальные задержки** между запросами
- **Graceful degradation** на mock данные
- **Автоматические повторы** при сбоях

## 📊 Логирование и статистика

### Система логирования
- **Файловые логи** в `logs/bot_operations.log`
- **Детальные записи** в таблице `order_logs`
- **Уведомления администраторов** о выполненных заказах
- **Конвертация валют** в рубли для статистики

### Метрики
- Количество выполненных заказов
- Общая выручка в рублях
- Средний чек
- Статистика по месяцам

## 🧪 Тестирование

### Запуск тестов
```bash
# Тесты основных компонентов
python3 test_bot.py

# Тесты парсеров
python3 test_parsers.py

# Тесты системы логирования
python3 test_logging.py
```

### Тестовые сценарии
- Обработка заказов с валидными данными
- Обработка заказов без Telegram username
- Недостаточный баланс Fragment
- Ошибки парсеров и API
- Система логирования и статистики

## 🚀 Развертывание

### Локальная разработка
```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка .env файла
cp env_example.txt .env
# Отредактируйте .env

# Запуск в mock режиме
python3 run.py
```

### Продакшен развертывание
```bash
# Настройка реальных аккаунтов
USE_MOCK_PARSERS=false
FUNPAY_LOGIN=your_real_login
FUNPAY_PASSWORD=your_real_password
FRAGMENT_PHONE=+your_real_phone

# Запуск с systemd
sudo systemctl enable telegram-stars-bot
sudo systemctl start telegram-stars-bot
```

## 📈 Мониторинг

### Логи
```bash
# Просмотр логов
tail -f logs/bot_operations.log

# Статус сервиса
sudo systemctl status telegram-stars-bot
```

### Метрики
- Количество активных заказов
- Время обработки заказов
- Частота ошибок
- Доступность парсеров

## 🔧 Конфигурация

### Основные параметры
- **`CURRENCY`** - Валюта офферов (RUB/USDT)
- **`FRAGMENT_MIN/MAX`** - Лимиты отправки Stars
- **`PAYMENT_WAIT_MINUTES`** - Время ожидания оплаты
- **`MAX_RETRY`** - Количество повторных попыток

### Парсеры
- **`USE_MOCK_PARSERS`** - Режим работы (true/false)
- **`BROWSER_HEADLESS`** - Headless режим браузера
- **`FUNPAY_LOGIN/PASSWORD`** - Данные FunPay
- **`FRAGMENT_PHONE`** - Номер телефона Fragment

## 🆘 Устранение неполадок

### Частые проблемы

#### Ошибки парсеров
```bash
# Включите mock режим для диагностики
USE_MOCK_PARSERS=true

# Проверьте логи
tail -f logs/bot_operations.log
```

#### Проблемы с базой данных
```bash
# Пересоздание базы
rm bot_database.db
python3 run.py
```

#### Ошибки авторизации
```bash
# Проверьте данные в .env
# Убедитесь в правильности логина/пароля
```

## 📚 Документация

- **[PARSERS_GUIDE.md](PARSERS_GUIDE.md)** - Подробное руководство по парсерам
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Инструкции по развертыванию
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Обзор проекта

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch
3. Внесите изменения
4. Добавьте тесты
5. Создайте Pull Request

## 📄 Лицензия

MIT License - см. файл [LICENSE](LICENSE)

## 🆘 Поддержка

- **Issues**: [GitHub Issues](https://github.com/your-username/Telegram-Bot-Stars/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/Telegram-Bot-Stars/discussions)

---

**Версия:** 1.0.0  
**Статус:** Готово к использованию  
**Последнее обновление:** 2024
