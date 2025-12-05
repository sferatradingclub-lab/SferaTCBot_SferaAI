# 🚀 SferaTC Bot + Sfera AI

**Telegram Bot экосистема для трейдеров** с интегрированным голосовым AI-ассистентом.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![LiveKit](https://img.shields.io/badge/LiveKit-Cloud-green.svg)](https://livekit.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Содержание

- [О проекте](#о-проекте)
- [Основные функции](#основные-функции)
- [Технологический стек](#технологический-стек)
- [Быстрый старт](#быстрый-старт)
- [Конфигурация](#конфигурация)
- [Развертывание](#развертывание)
- [Структура проекта](#структура-проекта)
- [Разработка](#разработка)

---

## 🎯 О проекте

**SferaTC Bot** - это Telegram бот с админ-панелью, инструментами для трейдинга и голосовым AI-ассистентом **Sfera AI**, который работает как Telegram Mini App.

### Основные компоненты:

1. **Telegram Bot** (Python) - основной бот с меню, командами и администрированием
2. **Sfera AI Agent** (Python + LiveKit) - голосовой AI-ассистент с мультиперсо system
3. **Mini App Frontend** (Next.js 15) - интерфейс Sfera AI в Telegram

---

## ✨ Основные функции

### Telegram Bot

#### 🤖 Sfera AI
- **Голосовой AI-ассистент** с памятью и базой знаний
- Запуск через Telegram Mini App (кнопка в меню)
- Multi-persona: Partner, Mentor, Psychologist
- Hybrid Knowledge Base search (Dense + Sparse vectors)

#### 🛠️ Полезные инструменты
- **Скидки на комиссии** - реферальные ссылки на криптобиржи

:
  - Tiger.com
  - Vataga Crypto
  - Whitelist Capital

> **Note:** Разделы "Скринеры", "Терминалы", "Снизить ping" - в разработке

#### 💬 Поддержка
- **Автоматический support** с LLM (база знаний о функциях бота)
- Эскалация к администратору
- История последних 10 обращений

#### 👑 Админ-панель
- **Статистика** (общая и за день)
- **Управление пользователями** (approve, ban, lookup)
- **Рассылки**:
  - Немедленная рассылка
  - Запланированная рассылка с календарем
  - Поддержка медиа (фото, видео, GIF)

### Sfera AI Agent

#### 🎭 Multi-Persona System

**1. Partner (Напарник)** - роль по умолчанию
- Проактивный помощник
- Быстрые, четкие ответы
- Немедленное выполнение команд

**2. Mentor (Наставник)**
- Сократический метод обучения
- Наводящие вопросы
- Развитие критического мышления
- **Триггеры:** "объясни", "как работает", "научи"

**3. Psychologist (Психолог)**
- Эмпатическая поддержка
- Техники КПТ (Когнитивно-Поведенческая Терапия)
- Работа с эмоциями (тильт, FOMO, страх)
- **Триггеры:** "тильт", "fomo", "паника", "нервы"

#### 🧠 Система памяти

- **Episodic Memory** - история всех разговоров
- **Core Memory** - ключевая информация о пользователе
- **Summary Memory** - сжатие предыдущих сессий
- **Qdrant Vector DB** для semantic search

#### 📚 База знаний

- **50+ документов** по трейдингу и психологии
- **Hybrid Search** (Dense + Sparse RRF)
- **Two-Stage Retrieval**:
  1. Discovery - находит релевантный summary
  2. Retrieval - загружает все шаги документа

#### 🔧 Инструменты агента

| Инструмент | Описание | Кеш |
|-----------|----------|-----|
| `search_knowledge_base` | Поиск в базе знаний | 30 мин |
| `search_web` | Google Custom Search | 10 мин |
| `get_crypto_price` | Binance API (real-time) | 30 сек |
| `get_weather` | wttr.in погода | Нет |
| `search_video` | DuckDuckGo video search | Нет |
| `send_email` | Gmail SMTP | Нет |
| `save_user_name` | Сохранение имени | Нет |
| `update_profile` | Обновление профиля | Нет |
| `start_plan` | Запуск обучающего плана | Нет |

---

## 🛠️ Технологический стек

### Backend (Telegram Bot)

```python
python-telegram-bot  # Telegram API
fastapi             # Web server для webhook + Mini App
sqlalchemy          # ORM для БД
httpx               # Async HTTP client
python-dotenv       # Environment variables
```

**Database:** PostgreSQL или SQLite

### Backend (Sfera AI)

```python
livekit-agents      # Voice AI framework
livekit-plugins-google  # Gemini integration
qdrant-client       # Vector database
fastembed==0.5.1    # Fast embeddings
aiohttp             # Async HTTP
duckduckgo-search   # Video search
sentry-sdk          # Error monitoring (optional)
```

**LLM:** Google Gemini 2.5 Flash (Native Audio)

### Frontend (Mini App)

```json
{
  "next": "15.x",
  "react": "19.x",
  "@livekit/components-react": "^2.x",
  "livekit-client": "^2.x",
  "motion": "^11.x",
  "tailwindcss": "^3.x"
}
```

---

## 🚀 Быстрый старт

### Предварительные требования

- Python 3.11+
- Node.js 18+
- PostgreSQL (опционально, можно SQLite)
- Accounts:
  - Telegram Bot Token
  - LiveKit Cloud
  - Google AI Studio (Gemini API)
  - Qdrant Cloud
  - Google Custom Search (опционально)

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd "SferaTC Bot + Sfera AI"
```

### 2. Установка зависимостей

#### Telegram Bot

```bash
# Виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка
pip install -r requirements.txt
```

#### Sfera AI

```bash
cd SferaAI_2
pip install -r requirements.txt
```

#### Frontend

```bash
cd SferaAI_2/frontend
npm install
```

### 3. Конфигурация

#### Основной `.env` (в корне)

```env
# === TELEGRAM BOT ===
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
BOT_USERNAME=YourBot_bot
ADMIN_CHAT_ID=123456789

# === DATABASE ===
# SQLite (для dev)
DATABASE_URL=sqlite:///./sferatc_dev.db
# PostgreSQL (для production)
# DATABASE_URL=postgresql://user:password@localhost/sferatc

# === WEBHOOK (для production) ===
WEBHOOK_URL=https://yourdomain.com
WEBHOOK_SECRET_TOKEN=your-secret-token
WEBHOOK_PORT=8443

# === OPENROUTER (для бесплатного ChatGPT в support) ===
OPENROUTER_API_KEY=sk-or-...

# === TELEGRAM CHANNEL ===
TELEGRAM_CHANNEL_URL=https://t.me/your_channel
```

#### `SferaAI_2/.env`

```env
# === LIVEKIT ===
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxxxxxxxxxxxxxx

# === GOOGLE GEMINI ===
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXX

# === QDRANT ===
QDRANT_HOST=https://xxxxx-xxxxx.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=xxxxxxxxxxxxxxxxxxxxxxx

# === GOOGLE SEARCH (опционально) ===
GOOGLE_CSE_ID=your-custom-search-engine-id

# === TELEGRAM (для auth в Mini App) ===
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# === MONITORING (опционально) ===
SENTRY_DSN=https://...@sentry.io/...
REDIS_URL=redis://...
```

### 4. Настройка Qdrant

```bash
cd SferaAI_2

# Создать коллекции
python scripts/setup_kb.py

# Загрузить данные KB
python scripts/ingest_kb_data.py
```

### 5. Сборка Frontend

```bash
cd SferaAI_2/frontend
npm run build

# Копировать в mini_app/public/
cd ../..
rm -rf mini_app/public/*
cp -r SferaAI_2/frontend/out/* mini_app/public/
```

### 6. Запуск

#### Development (Polling)

```bash
# Terminal 1: Telegram Bot
python main.py

# Terminal 2: Sfera AI Agent
cd SferaAI_2
python agent.py
```

#### Production (Webhook)

```bash
# С systemd (см. раздел Развертывание)
sudo systemctl start sferatc-bot
sudo systemctl start sfera-agent
```

---

## ⚙️ Конфигурация

### Telegram Bot Settings

Все настройки находятся в `config.py`:

```python
@dataclass
class Settings:
    # Core
    TELEGRAM_TOKEN: str
    ADMIN_CHAT_ID: str
    DATABASE_URL: str
    
    # Webhook
    WEBHOOK_URL: Optional[str]
    WEBHOOK_PORT: int = 8443
    WEBHOOK_SECRET_TOKEN: Optional[str]
    
    # ChatGPT (OpenRouter)
    OPENROUTER_API_KEY: Optional[str]
    CHATGPT_MODELS: List[str]  # Free models
    
    # Tools
    TOOLS_DATA: Dict[str, Any]  # Trading tools config
    
    # Support
    SUPPORT_LLM_ENABLED: bool = True
    
    # Media URLs
    WELCOME_IMAGE_URL: Optional[str]
    TOOLS_IMAGE_URL: Optional[str]
    ...
```

### Sfera AI Config

Файл `SferaAI_2/config.py`:

```python
@dataclass
class Config:
    # Memory
    memory: MemoryConfig
    
    # Knowledge Base
    kb: KBConfig
    
    # Timeouts
    GOOGLE_SEARCH_TIMEOUT: int = 8
    WEATHER_TIMEOUT: int = 6
    
    # Validation
    def validate(self) -> Dict[str, Any]:
        ...
```

---

## 🌐 Развертывание

### Production Setup (Linux)

#### 1. Systemd Service - Telegram Bot

`/etc/systemd/system/sferatc-bot.service`:

```ini
[Unit]
Description=SferaTC Telegram Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/project
Environment="PATH=/path/to/project/venv/bin"
ExecStart=/path/to/project/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 2. Systemd Service - Sfera AI Agent

`/etc/systemd/system/sfera-agent.service`:

```ini
[Unit]
Description=Sfera AI LiveKit Agent
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/project/SferaAI_2
Environment="PATH=/path/to/project/venv/bin"
ExecStart=/path/to/project/venv/bin/python agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 3. Запуск сервисов

```bash
sudo systemctl daemon-reload
sudo systemctl enable sferatc-bot sfera-agent
sudo systemctl start sferatc-bot sfera-agent

# Проверка статуса
sudo systemctl status sferatc-bot
sudo systemctl status sfera-agent

# Логи
sudo journalctl -u sferatc-bot -f
sudo journalctl -u sfera-agent -f
```

#### 4. Nginx (для Mini App + Webhook)

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Mini App
    location / {
        proxy_pass http://localhost:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Webhook
    location /webhook {
        proxy_pass http://localhost:8443/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📁 Структура проекта

```
SferaTC Bot + Sfera AI/
├── main.py                    # Entry point (FastAPI + PTB)
├── config.py                  # Settings & validation
├── keyboards.py               # Telegram keyboards
├── requirements.txt           # Python dependencies
│
├── handlers/                  # Command & message handlers
│   ├── common_handlers.py     # /start, /help, routing
│   ├── admin_handlers.py      # Admin panel
│   ├── sfera_handlers.py      # Sfera AI launcher
│   ├── tools_handlers.py      # Trading tools
│   ├── admin/                 # Admin submodules
│   └── user/
│       └── support_handler.py # LLM support
│
├── services/                  # Business logic
│   ├── chatgpt_service.py     # OpenRouter streaming
│   ├── broadcast_scheduler.py # Scheduled broadcasts
│   ├── cache_service.py       # ChatGPT caching
│   └── ...
│
├── models/                    # SQLAlchemy models
│   ├── user.py
│   ├── broadcast.py
│   └── crud.py
│
├── mini_app/                  # Mini App static files
│   └── public/                # Built frontend (from SferaAI_2/frontend/out)
│
├── SferaAI_2/                 # Sfera AI Agent
│   ├── agent.py               # LiveKit agent entrypoint
│   ├── prompts.py             # Multi-persona prompts
│   ├── tools.py               # Agent tools
│   ├── knowledge_base.py      # KB hybrid search
│   ├── qdrant_memory_client.py # Memory system
│   ├── unified_user_state.py  # User state + profiles
│   ├── config.py              # Agent config
│   ├── requirements.txt       # Agent dependencies
│   │
│   ├── agent/                 # Modular components
│   │   ├── assistant.py
│   │   ├── memory_loader.py
│   │   └── session_manager.py
│   │
│   ├── data/                  # Knowledge base & courses
│   │   └── knowledge_base_unified/
│   │       └── MASTER_*.md    # 50+ documents
│   │
│   ├── frontend/              # Next.js 15 Mini App
│   │   ├── app/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── next.config.ts
│   │   ├── package.json
│   │   └── out/               # Build output
│   │
│   └── scripts/
│       ├── setup_kb.py        # Create Qdrant collections
│       └── ingest_kb_data.py  # Load KB data
│
└── .env                       # Environment variables
```

---

## 👨‍💻 Разработка

### Локальное тестирование Mini App

Для тестирования Mini App локально используйте ngrok:

1. Запустите бота в webhook mode:
   ```bash
   # В .env установите:
   WEBHOOK_URL=https://your-ngrok-url.ngrok-free.app
   
   # Запустите бота
   python main.py
   ```

2. В другом терминале:
   ```bash
   ngrok http 8443
   # Скопируйте HTTPS URL в WEBHOOK_URL
   ```

3. Перезапустите бота

4. Откройте бота в Telegram и нажмите "🤖 Sfera AI"

### Debugging

#### Telegram Bot

```python
# main.py - включить подробные логи
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Sfera AI Agent

```python
# agent.py
logging.basicConfig(level=logging.INFO)

# Для debug агента
logging.getLogger("livekit").setLevel(logging.DEBUG)
```

#### Frontend

```bash
cd SferaAI_2/frontend
npm run dev
# → http://localhost:3000
```

### Добавление новых инструментов в Sfera AI

1. Создайте инструмент в `tools.py`:

```python
@function_tool()
async def my_new_tool(context: RunContext, param: str) -> str:
    """Tool description for LLM."""
    # Your logic
    return result
```

2. Зарегистрируйте в `agent.py`:

```python
from tools import ..., my_new_tool

extra_tools = [..., my_new_tool]
```

3. Обновите system prompt в `prompts.py` (если нужно)

### Добавление документов в Knowledge Base

1. Создайте `.md` файл в `SferaAI_2/data/knowledge_base_unified/`:

```markdown
---
id: my_new_doc
title: "Название документа"
category_1: trading  # или psychology
category_2: breakouts  # подкатегория
difficulty_level: beginner  # или intermediate, advanced
---

# Summary
Краткое описание...

# Step 1: Заголовок
Контент шага 1...

# Step 2: Заголовок
Контент шага 2...
```

2. Запустите инжест:

```bash
cd SferaAI_2
python scripts/ingest_kb_data.py
```

---

## 🐛 Troubleshooting

### Ошибка: `unified_state is not defined`

**Решение:** Убедитесь, что используете актуальную версию `agent.py` после bug fix (см. commit history)

### Ошибка: `VideoTrack` не отображается

**Решение:** Проверьте импорт в `session-view.tsx`:
```typescript
import { ..., VideoTrack } from '@livekit/components-react';
```

### Ошибка: Duplicate function `get_chatgpt_response`

**Решение:** Исправлено в последней версии `services/chatgpt_service.py`

### Mini App не открывается

1. Проверьте `WEBHOOK_URL` в `.env`
2. Проверьте, что frontend собран:
   ```bash
   ls mini_app/public/index.html
   ```
3. Проверьте CORS headers в `main.py`

### Qdrant ошибки

#### `400 Bad Request: No index for timestamp`

```bash
cd SferaAI_2
python scripts/setup_kb.py  # Пересоздать с индексами
```

#### Connection timeout

Проверьте `QDRANT_HOST` и `QDRANT_API_KEY` в `.env`

---

## 📄 Лицензия

MIT License - см. [LICENSE](LICENSE)

---

## 🤝 Contributing

Pull requests приветствуются! Для больших изменений сначала откройте issue.

---

## 📞 Контакты

- Telegram Channel: [Указать ссылку]
- Support: [Указать контакт]

---

**Made with ❤️ by SferaTC Team**
