# Руководство по установке и запуску

## Системные требования

### Минимальные требования
- **Операционная система:** Linux, macOS, или Windows
- **Процессор:** 1 GHz или выше
- **Оперативная память:** 512 MB минимум, рекомендуется 1 GB
- **Дисковое пространство:** 200 MB свободного места
- **Сеть:** Доступ к интернету для API вызовов

### Рекомендуемые требования
- **Операционная система:** Linux (Ubuntu 20.04+ или CentOS 8+)
- **Процессор:** 2 GHz многопроцессорный
- **Оперативная память:** 2 GB или больше
- **Дисковое пространство:** 1 GB свободного места
- **Сеть:** Стабильное интернет-соединение

## Предварительные требования

### 1. Python 3.9+
Убедитесь, что у вас установлен Python 3.9 или выше:

```bash
python3 --version
# Должно вывести: Python 3.9.0 или выше
```

Если Python не установлен, скачайте его с [официального сайта](https://python.org/downloads/).

### 2. PostgreSQL (рекомендуется)
Для продакшена рекомендуется использовать PostgreSQL:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql-server postgresql-contrib
sudo postgresql-setup initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 3. Git
Для клонирования репозитория:

```bash
# Ubuntu/Debian
sudo apt install git

# CentOS/RHEL
sudo yum install git

# macOS
brew install git

# Windows
# Скачайте с https://git-scm.com/download/win
```

## Установка проекта

### Шаг 1: Клонирование репозитория

```bash
git clone <URL_репозитория>
cd sferatc-bot
```

### Шаг 2: Создание виртуального окружения

```bash
# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### Шаг 3: Установка зависимостей

```bash
pip install -r requirements.txt
```

Если возникнут проблемы с установкой, попробуйте обновить pip:

```bash
pip install --upgrade pip
```

### Шаг 4: Настройка базы данных

#### Вариант 1: PostgreSQL (рекомендуется для продакшена)

1. Создайте базу данных и пользователя:

```sql
-- Подключитесь к PostgreSQL
sudo -u postgres psql

-- Создайте базу данных
CREATE DATABASE sferatc_db;

-- Создайте пользователя
CREATE USER sferatc_user WITH PASSWORD 'your_secure_password';

-- Предоставьте права
GRANT ALL PRIVILEGES ON DATABASE sferatc_db TO sferatc_user;

-- Выйдите из PostgreSQL
\q
```

2. Обновите переменные окружения в файле `.env`:

```env
DATABASE_URL=postgresql://sferatc_user:your_secure_password@localhost/sferatc_db
```

#### Вариант 2: SQLite (для разработки)

По умолчанию проект использует SQLite. Просто убедитесь, что в `.env` указан правильный путь:

```env
DATABASE_URL=sqlite:///./sferatc_dev.db
```

### Шаг 5: Настройка переменных окружения

1. Скопируйте пример файла окружения:

```bash
cp .env.example .env
```

2. Отредактируйте файл `.env` со своими настройками:

```bash
nano .env  # или используйте любой текстовый редактор
```

Обязательные переменные:

```env
# Telegram Bot
TELEGRAM_TOKEN=ваш_токен_от_BotFather
ADMIN_CHAT_ID=ваш_telegram_id_как_администратора

# База данных
DATABASE_URL=postgresql://user:password@localhost/sferatc_db

# OpenRouter API (для ChatGPT функций)
OPENROUTER_API_KEY=ваш_openrouter_api_ключ

# Опционально: вебхуки
WEBHOOK_URL=https://ваш-домен.com
WEBHOOK_SECRET_TOKEN=ваш_секретный_токен
```

### Шаг 6: Инициализация базы данных

```bash
python migrate.py
```

Эта команда создаст все необходимые таблицы в базе данных.

## Запуск приложения

### Режим разработки (Polling)

```bash
python main.py
```

В этом режиме бот будет получать обновления через длинный polling. Подходит для разработки и тестирования.

### Режим продакшена (Вебхуки)

1. Настройте веб-сервер (nginx + uvicorn рекомендуется):

```bash
# Установите uvicorn если не установлен
pip install uvicorn

# Запустите сервер
uvicorn main:asgi_app --host 0.0.0 --port 8443
```

2. Настройте nginx (пример конфигурации):

```nginx
server {
    listen 80;
    server_name ваш-домен.com;

    location / {
        proxy_pass http://127.0.0.1:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. Настройте вебхук в Telegram:

```bash
curl -F "url=https://ваш-домен.com/TELEGRAM_TOKEN" \
     -F "secret_token=ваш_секретный_токен" \
     https://api.telegram.org/botTELEGRAM_TOKEN/setWebhook
```

## Проверка работоспособности

### 1. Проверка бота

Отправьте команду `/start` боту в Telegram. Вы должны получить приветственное сообщение.

### 2. Проверка веб-интерфейса

Откройте браузер и перейдите по адресу `https://ваш-домен.com`. Вы должны увидеть мини-приложение.

### 3. Проверка API

```bash
# Проверьте статус вебхука
curl https://api.telegram.org/botTELEGRAM_TOKEN/getWebhookInfo

# Должен вернуть информацию о настроенном вебхуке
```

## Диагностика проблем

### Проблемы с запуском

1. **Ошибка импорта модулей:**
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

2. **Ошибка подключения к базе данных:**
   - Проверьте настройки в `.env`
   - Убедитесь, что база данных запущена и доступна

3. **Ошибка токена Telegram:**
   - Проверьте правильность токена в `.env`
   - Убедитесь, что токен активен у @BotFather

### Проблемы с производительностью

1. **Высокое потребление памяти:**
   - Проверьте настройки кеширования в `config.py`
   - Мониторьте количество активных сессий

2. **Медленные ответы:**
   - Проверьте настройки rate limiting
   - Оптимизируйте запросы к базе данных

### Логи и отладка

Бот ведет подробное логирование. Логи можно найти в:
- Консоль (при запуске в режиме разработки)
- Файл `bot.log` (если включено логирование в файл)

Для более детального логирования установите уровень DEBUG:

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

## Обновление проекта

### Шаг 1: Создание резервной копии

```bash
cp .env .env.backup
pg_dump sferatc_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Шаг 2: Обновление кода

```bash
git pull origin main
```

### Шаг 3: Обновление зависимостей

```bash
pip install -r requirements.txt --upgrade
```

### Шаг 4: Применение миграций

```bash
python migrate.py
```

### Шаг 5: Перезапуск приложения

```bash
# Остановите текущий процесс
Ctrl+C

# Запустите заново
python main.py
```

## Безопасность

### Рекомендации по безопасности

1. **Храните секреты безопасно:**
   - Используйте сильные пароли
   - Не коммитьте `.env` в репозиторий
   - Регулярно меняйте API ключи

2. **Настройте firewall:**
   ```bash
   sudo ufw allow 22
   sudo ufw allow 80
   sudo ufw allow 443
   sudo ufw enable
   ```

3. **Используйте SSL сертификаты:**
   ```bash
   # Получите бесплатный сертификат от Let's Encrypt
   sudo certbot --nginx -d ваш-домен.com
   ```

4. **Мониторинг:**
   - Настройте мониторинг ресурсов сервера
   - Включите уведомления о критических ошибках
   - Регулярно проверяйте логи на подозрительную активность

## Поддержка

Если у вас возникли проблемы:

1. Проверьте логи приложения
2. Убедитесь, что все зависимости установлены
3. Проверьте настройки в `.env`
4. Создайте issue в репозитории с детальным описанием проблемы

---

**Последнее обновление:** Октябрь 2025