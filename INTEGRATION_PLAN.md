# 📋 План интеграции Sfera AI в Telegram Bot как Mini App

> **Дата создания:** 01.12.2025  
> **Версия:** 1.0

---

## 🎯 Что у тебя есть:

1. **Telegram Bot** - работающий бот с функциями обучения, ChatGPT, поддержки и т.д.
2. **Sfera AI** - голосовой AI-ассистент на Next.js с LiveKit
3. **Mini App папка** - уже есть структура для mini-app в телеграм боте

---

## ✅ Пошаговый план интеграции:

### **Этап 1: Подготовка Frontend Sfera AI**

**Цель**: Адаптировать Next.js приложение для работы внутри Telegram Mini App

#### Шаг 1.1: Добавить Telegram SDK в Sfera AI

```bash
cd SferaAI_2/frontend
npm install @twa-dev/sdk
```

**Что сделать в коде:**
- Добавить инициализацию Telegram Web App API в главном компоненте
- Настроить тему в соответствии с темой Telegram
- Добавить обработку кнопок Telegram (например, кнопки "Назад")

**Пример кода для интеграции:**
```typescript
// В app/layout.tsx или app/page.tsx
import WebApp from '@twa-dev/sdk'

useEffect(() => {
  if (typeof window !== 'undefined') {
    WebApp.ready()
    WebApp.expand()
    // Настройка темы
    WebApp.setHeaderColor('bg_color')
  }
}, [])
```

#### Шаг 1.2: Настроить Next.js для static export

**Обновить `next.config.ts`:**
```typescript
const nextConfig = {
  output: 'export',
  images: {
    unoptimized: true,
  },
}

export default nextConfig
```

#### Шаг 1.3: Собрать production build

```bash
cd SferaAI_2/frontend
npm run build
# После сборки проверить папку 'out'
```

---

### **Этап 2: Интеграция в структуру телеграм бота**

**Цель**: Заменить текущее мини-приложение на Sfera AI

#### Шаг 2.1: Скопировать собранный frontend

```bash
# Очистить старое содержимое
rm -rf mini_app/public/*

# Скопировать новое (Windows PowerShell)
Copy-Item -Path "SferaAI_2\frontend\out\*" -Destination "mini_app\public\" -Recurse

# Или вручную скопировать содержимое папки SferaAI_2/frontend/out в mini_app/public
```

#### Шаг 2.2: Проверить FastAPI конфигурацию

**Открыть `main.py` и проверить секцию с мини-приложением:**

```python
# Должно быть примерно так:
MINI_APP_PUBLIC_DIR = Path(__file__).resolve().parent / "mini_app" / "public"
MINI_APP_STATIC_ROUTE = "/mini-app/static"

asgi_app.mount(
    MINI_APP_STATIC_ROUTE,
    StaticFiles(directory=MINI_APP_PUBLIC_DIR),
    name="mini_app_static",
)

@asgi_app.get("/", include_in_schema=False)
async def serve_mini_app() -> FileResponse:
    response = FileResponse(MINI_APP_PUBLIC_DIR / "index.html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response
```

---

### **Этап 3: Backend интеграция**

**Цель**: Запускать Python агент Sfera AI вместе с телеграм ботом

#### Шаг 3.1: Объединить зависимости

**Открыть `SferaAI_2/requirements.txt` и добавить все зависимости в корневой `requirements.txt`:**

Основные зависимости Sfera AI:
```
livekit
livekit-agents[openai]
livekit-plugins-google
livekit-plugins-deepgram
livekit-plugins-silero
qdrant-client
python-dotenv
fastembed
```

#### Шаг 3.2: Установить все зависимости

```bash
# В корне проекта
pip install -r requirements.txt
```

#### Шаг 3.3: Перенести код агента

**Вариант A: Создать отдельный модуль**
```bash
# Создать папку sfera_agent в корне проекта
mkdir sfera_agent

# Скопировать файлы из SferaAI_2:
# - agent.py → sfera_agent/sfera_agent.py
# - prompts.py → sfera_agent/prompts.py
# - tools.py → sfera_agent/tools.py
# - knowledge_base.py → sfera_agent/knowledge_base.py
# - qdrant_memory_client.py → sfera_agent/qdrant_memory_client.py
# И другие необходимые файлы
```

**Вариант B: Использовать существующий код**
```bash
# Просто скопировать всю папку SferaAI_2 в корень проекта
# И импортировать из неё
```

#### Шаг 3.4: Создать скрипт запуска агента

**Создать файл `run_sfera_agent.py` в корне проекта:**

```python
"""
Запуск LiveKit агента Sfera AI
"""
import asyncio
from pathlib import Path
import sys

# Добавляем путь к модулю Sfera AI
sys.path.insert(0, str(Path(__file__).parent / "SferaAI_2"))

from SferaAI_2.agent import main as agent_main

if __name__ == "__main__":
    asyncio.run(agent_main())
```

#### Шаг 3.5: Настроить параллельный запуск

**Вариант A: Использовать два терминала**
```bash
# Терминал 1: Telegram Bot
python main.py

# Терминал 2: Sfera AI Agent
python run_sfera_agent.py
```

**Вариант B: Создать supervisor скрипт**
```python
# supervisor.py
import subprocess
import sys

def main():
    processes = [
        subprocess.Popen([sys.executable, "main.py"]),
        subprocess.Popen([sys.executable, "run_sfera_agent.py"])
    ]
    
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        for process in processes:
            process.terminate()

if __name__ == "__main__":
    main()
```

**Вариант C: Использовать systemd (для продакшена)**

---

### **Этап 4: Настройка переменных окружения**

**Цель**: Объединить конфигурации обоих проектов

#### Шаг 4.1: Объединить .env файлы

**Открыть корневой `.env` и добавить переменные из `SferaAI_2/.env`:**

```env
# ============================================
# Telegram Bot Configuration
# ============================================
TELEGRAM_TOKEN=your_bot_token_here
ADMIN_CHAT_ID=your_admin_chat_id
DATABASE_URL=postgresql://user:password@localhost/sferatc_db
OPENROUTER_API_KEY=your_openrouter_key
WEBHOOK_URL=https://your-domain.com
WEBHOOK_SECRET_TOKEN=your_webhook_secret

# ============================================
# Sfera AI Configuration
# ============================================

# LiveKit Cloud
LIVEKIT_URL=wss://your-cluster.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# Google Gemini
GOOGLE_API_KEY=your_google_api_key

# Qdrant Cloud
QDRANT_HOST=https://your-qdrant-cluster-url.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key

# Optional: Sentry (for monitoring)
# SENTRY_DSN=your_sentry_dsn

# Optional: Redis (for session registry)
# REDIS_URL=your_redis_url
```

#### Шаг 4.2: Обновить .env.example

Не забудь обновить `.env.example` с новыми переменными для других разработчиков.

---

### **Этап 5: Добавление кнопки в бот**

**Цель**: Дать пользователям доступ к Sfera AI

#### Шаг 5.1: Создать handler для Sfera AI

**Создать файл `handlers/sfera_handlers.py`:**

```python
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import get_settings

settings = get_settings()

async def show_sfera_ai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает кнопку для запуска Sfera AI Mini App."""
    
    # URL вашего мини-приложения
    # Для локальной разработки используйте ngrok или подобное
    # Для продакшена - ваш домен
    mini_app_url = settings.WEBHOOK_URL or "https://your-domain.com"
    
    keyboard = [
        [InlineKeyboardButton(
            text="🤖 Запустить Sfera AI",
            web_app=WebAppInfo(url=mini_app_url)
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎙️ <b>Sfera AI - Твой голосовой ассистент</b>\n\n"
        "Нажми кнопку ниже, чтобы общаться с AI в режиме реального времени:\n\n"
        "✨ Голосовой интерфейс\n"
        "🧠 Помнит предыдущие разговоры\n"
        "📚 Использует базу знаний\n"
        "🛠️ Может искать информацию в интернете",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
```

#### Шаг 5.2: Зарегистрировать handler в main.py

**В `main.py` добавить:**

```python
# В импортах
from handlers.sfera_handlers import show_sfera_ai

# В функции main(), перед return application
application.add_handler(CommandHandler("sfera", show_sfera_ai))

# Также можно добавить кнопку в главное меню
application.add_handler(
    MessageHandler(
        filters.TEXT & filters.Regex("^🤖 Sfera AI$"),
        show_sfera_ai,
    )
)
```

#### Шаг 5.3: Обновить клавиатуру главного меню

**В `keyboards.py` добавить кнопку:**

```python
def get_main_menu_keyboard():
    """Возвращает основную клавиатуру меню."""
    keyboard = [
        ["Пройти бесплатное обучение"],
        ["ИИ-психолог", "Полезные инструменты"],
        ["Бесплатный ChatGPT", "🤖 Sfera AI"],  # Добавили Sfera AI
        ["Поддержка"],
    ]
    # Добавить кнопку админки для администраторов можно динамически
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
```

---

### **Этап 6: Тестирование**

#### Шаг 6.1: Локальное тестирование

**Чеклист:**
- [ ] Бот запускается без ошибок (`python main.py`)
- [ ] Агент Sfera AI запускается без ошибок (`python run_sfera_agent.py`)
- [ ] Команда `/sfera` или кнопка "🤖 Sfera AI" работает
- [ ] Мини-приложение открывается в Telegram
- [ ] Голосовой интерфейс работает (микрофон, распознавание, ответ)
- [ ] База знаний отвечает на вопросы правильно
- [ ] Память работает (агент помнит предыдущие сообщения)

**Для локального тестирования Mini App в Telegram:**
1. Используй `ngrok` или `cloudflared` для публикации локального сервера
   ```bash
   ngrok http 8000  # если бот на порту 8000
   ```
2. Укажи полученный URL в настройках бота у @BotFather
3. Обнови `WEBHOOK_URL` в `.env`

#### Шаг 6.2: Проверка функционала

**Тестовые сценарии:**

1. **Голосовое общение:**
   - Запусти мини-приложение
   - Разреши доступ к микрофону
   - Скажи "Привет"
   - Проверь, что агент отвечает голосом

2. **База знаний:**
   - Спроси "Расскажи о психологии трейдинга"
   - Проверь, что ответ идёт из базы знаний

3. **Память:**
   - Скажи "Меня зовут Алекс"
   - Закрой приложение
   - Открой заново
   - Спроси "Как меня зовут?"
   - Проверь, что агент помнит

4. **Инструменты:**
   - Спроси "Какая погода в Москве?"
   - Спроси "Какой курс биткоина?"
   - Проверь, что данные актуальные

#### Шаг 6.3: Деплой на сервер

**Для продакшена:**

1. **Подготовить сервер**
   - Ubuntu/Debian или CentOS
   - Python 3.11+
   - PostgreSQL (если используется)
   - Nginx (для reverse proxy)

2. **Настроить systemd сервисы**

**Файл `/etc/systemd/system/telegram-bot.service`:**
```ini
[Unit]
Description=SferaTC Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/project
Environment="PATH=/path/to/project/.venv/bin"
ExecStart=/path/to/project/.venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Файл `/etc/systemd/system/sfera-agent.service`:**
```ini
[Unit]
Description=Sfera AI LiveKit Agent
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/project
Environment="PATH=/path/to/project/.venv/bin"
ExecStart=/path/to/project/.venv/bin/python run_sfera_agent.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. **Запустить сервисы**
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot sfera-agent
sudo systemctl start telegram-bot sfera-agent
sudo systemctl status telegram-bot sfera-agent
```

---

## 📁 Итоговая структура проекта:

```
SferaTC Bot + Sfera AI/
├── .env                       # Объединённые переменные окружения
├── .env.example               # Пример конфигурации
├── main.py                    # Основной файл телеграм бота
├── run_sfera_agent.py         # Запуск LiveKit агента
├── supervisor.py              # (Опционально) Запуск обоих сервисов
├── config.py                  # Конфигурация (объединённая)
├── requirements.txt           # Все зависимости
├── 
├── handlers/                  # Обработчики телеграм бота
│   ├── common_handlers.py
│   ├── admin_handlers.py
│   ├── sfera_handlers.py      # ← НОВЫЙ файл для Sfera AI
│   └── ...
├── 
├── services/                  # Сервисы бота
├── models/                    # Модели базы данных
├── keyboards.py               # Обновлённый с кнопкой Sfera AI
├── 
├── mini_app/                  # Мини-приложение
│   ├── public/                # ← Frontend Sfera AI (собранный)
│   │   ├── index.html
│   │   ├── _next/
│   │   │   ├── static/
│   │   │   └── ...
│   │   └── ...
│   └── README.md
├── 
├── SferaAI_2/                 # Исходный код Sfera AI
│   ├── agent.py               # LiveKit агент
│   ├── prompts.py             # Промпты агента
│   ├── tools.py               # Инструменты агента
│   ├── knowledge_base.py      # Работа с базой знаний
│   ├── qdrant_memory_client.py # Клиент для Qdrant
│   ├── frontend/              # Next.js приложение (исходники)
│   └── scripts/               # Скрипты
│       ├── setup_kb.py
│       └── ingest_kb_data.py
├── 
└── scripts/                   # Общие скрипты
```

---

## 🔑 Ключевые моменты:

### ✅ Что нужно помнить:

1. **Next.js нужно собрать в static export**
   - Настроить `output: 'export'` в `next.config.ts`
   - Запустить `npm run build`
   - Результат будет в папке `out/`

2. **LiveKit агент запускается отдельным процессом**
   - Параллельно с телеграм ботом
   - Использует те же переменные окружения
   - Подключается к LiveKit Cloud

3. **База данных Qdrant - облачная**
   - Доступна из любого места
   - Одинаковые данные для всех инстансов
   - Нужен только API ключ

4. **Конфигурации объединяются**
   - Один `.env` файл для всего проекта
   - Все переменные в одном месте
   - Легко управлять

5. **Telegram Mini App WebView**
   - Просто открывает URL с мини-приложением
   - Поддерживает весь функционал браузера
   - Интеграция через `@twa-dev/sdk`

---

## ⚡ Быстрый старт (краткая инструкция):

```bash
# 1. Подготовить frontend
cd SferaAI_2/frontend
npm install @twa-dev/sdk
# Обновить next.config.ts (добавить output: 'export')
npm run build

# 2. Скопировать в mini_app
cd ../..
rm -rf mini_app/public/*
cp -r SferaAI_2/frontend/out/* mini_app/public/

# 3. Объединить зависимости
cat SferaAI_2/requirements.txt >> requirements.txt
pip install -r requirements.txt

# 4. Объединить .env
cat SferaAI_2/.env >> .env

# 5. Создать handler для Sfera AI
# (Создать handlers/sfera_handlers.py и обновить main.py)

# 6. Запустить оба сервиса
python main.py &  # Telegram Bot
python run_sfera_agent.py &  # Sfera AI Agent
```

---

## 🚧 Возможные проблемы и решения:

### Проблема 1: Next.js не собирается с `output: 'export'`
**Решение:** Проверь, что не используешь серверные функции Next.js (API routes, getServerSideProps и т.д.)

### Проблема 2: Мини-приложение не открывается в Telegram
**Решение:** Убедись, что:
- URL доступен по HTTPS
- Настроен правильный домен у @BotFather
- Нет CORS ошибок (проверь в консоли браузера)

### Проблема 3: LiveKit агент не подключается
**Решение:** Проверь переменные окружения `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`

### Проблема 4: Qdrant не работает
**Решение:** Проверь `QDRANT_HOST` и `QDRANT_API_KEY`, убедись что коллекции созданы (`python scripts/setup_kb.py`)

### Проблема 5: Голос не работает в Telegram
**Решение:** Telegram WebView поддерживает WebRTC, но нужно разрешение пользователя на микрофон

---

## 📝 Чеклист перед запуском:

- [ ] Frontend собран в static export (`npm run build`)
- [ ] Файлы скопированы в `mini_app/public/`
- [ ] Все зависимости установлены (`pip install -r requirements.txt`)
- [ ] `.env` файл содержит все необходимые переменные
- [ ] Handler для Sfera AI создан и зарегистрирован
- [ ] Кнопка добавлена в главное меню
- [ ] LiveKit агент запускается без ошибок
- [ ] Telegram Bot запускается без ошибок
- [ ] Qdrant коллекции созданы и заполнены
- [ ] Протестирован локально с ngrok
- [ ] Готов к деплою на сервер

---

## 📞 Поддержка и документация:

- **Telegram Bot API:** https://core.telegram.org/bots/api
- **Telegram Mini Apps:** https://core.telegram.org/bots/webapps
- **LiveKit Docs:** https://docs.livekit.io/
- **Next.js Static Export:** https://nextjs.org/docs/app/building-your-application/deploying/static-exports
- **Qdrant Docs:** https://qdrant.tech/documentation/

---

**Версия документа:** 1.0  
**Последнее обновление:** 01.12.2025  
**Автор:** AI Assistant

---

**Удачи с интеграцией! 🚀**
