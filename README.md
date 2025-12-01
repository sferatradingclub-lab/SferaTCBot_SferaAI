# SferaTC Telegram Bot + Sfera AI

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Telegram-бот для экосистемы SferaTC с интеграцией **Sfera AI** - голосового ИИ-ассистента на базе OpenAI Realtime API и LiveKit.

## ✨ Возможности

### 🤖 Sfera AI - Голосовой ИИ-ассистент
- **Голосовое общение** - общайтесь с ИИ голосом в реальном времени
- **Telegram Mini App** - полноценное веб-приложение внутри Telegram
- **LiveKit интеграция** - низкая задержка и высокое качество аудио
- **OpenAI Realtime API** - продвинутый голосовой ИИ
- **Киберпанк UI** - стильный интерфейс с 3D визуализацией

### 👥 Пользовательские функции
- **Система обучения** - доступ к образовательным материалам
- **Поддержка** - прямая связь с администратором
- **Mini App** - веб-интерфейс для Sfera AI

### 🛠️ Инструменты для трейдинга
- **Дисконтные брокеры** - ссылки на Tiger.com, Vataga Crypto
- **Скринеры** - инструменты для анализа рынка
- **Торговые терминалы** - профессиональные платформы

### 👨‍💼 Администрирование
- **Панель администратора** - управление ботом
- **Система поддержки** - обработка обращений пользователей
- **Управление пользователями** - модерация

## 🏗️ Архитектура

```
sferatc-bot/
├── handlers/              # Обработчики команд
│   ├── admin/            # Административные функции
│   ├── sfera_handlers.py # Sfera AI интеграция
│   ├── common_handlers.py # Общие команды
│   ├── tools_handlers.py # Инструменты трейдинга
│   └── states.py         # FSM состояния
├── services/             # Бизнес-логика
│   ├── state_manager.py  # Управление состояниями
│   ├── user_service.py   # Работа с пользователями
│   └── notifier.py       # Уведомления
├── models/               # База данных
│   ├── user.py          # Модель пользователя
│   └── crud.py          # CRUD операции
├── mini_app/            # Sfera AI Mini App
│   └── public/          # Статические файлы (из SferaAI_2/frontend/out)
├── SferaAI_2/           # Sfera AI Agent (submodule)
│   ├── agent.py         # Голосовой ИИ агент
│   ├── frontend/        # Next.js приложение
│   └── requirements.txt # Python зависимости
├── config.py            # Конфигурация
├── main.py              # Точка входа
└── requirements.txt     # Зависимости бота
```

## 🛠️ Установка

### Предварительные требования
- Python 3.9+
- Node.js 18+ (для разработки frontend)
- PostgreSQL или SQLite
- Telegram Bot Token (от @BotFather)
- LiveKit Cloud account (для Sfera AI)

### Быстрый старт

1. **Клонируйте репозиторий:**
```bash
git clone https://github.com/sferatradingclub-lab/SferaTCBot_SferaAI.git
cd SferaTCBot_SferaAI
```

2. **Установите зависимости бота:**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

3. **Настройте переменные окружения:**
```bash
cp .env.example .env
# Отредактируйте .env
```

Обязательные переменные:
```env
TELEGRAM_TOKEN=your_bot_token
ADMIN_CHAT_ID=your_admin_id
DATABASE_URL=sqlite:///sfera.db
WEBHOOK_URL=https://your-domain.com  # Для Sfera AI Mini App
```

4. **Запустите бота:**
```bash
python main.py
```

### Развертывание Sfera AI (опционально)

Sfera AI агент находится в подмодуле `SferaAI_2/`:

```bash
cd SferaAI_2
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
python agent.py dev  # Запуск в режиме разработки
```

Frontend уже собран и находится в `mini_app/public/`.

## 📱 Команды бота

### Пользовательские
- `/start` - начать работу
- `/help` - справка
- `/training` - обучение
- `/tools` - инструменты трейдинга
- `/sfera` - запустить Sfera AI
- `/support` - обратиться в поддержку

### Административные
- `/admin` - панель админа
- `/stats` — статистика
- `/status` - статус системы

## 🚀 Deployment

### На сервере

1. **Клонируйте репозиторий** на сервер

2. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

3. **Настройте переменные окружения**

4. **Настройте systemd service** (Linux):
```ini
[Unit]
Description=SferaTC Telegram Bot
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/bot
ExecStart=/path/to/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

5. **Запустите:**
```bash
sudo systemctl start sferatc-bot
sudo systemctl enable sferatc-bot
```

### Sfera AI Mini App

Mini App требует HTTPS! Используйте:
- **ngrok** для локального тестирования
- **Nginx + Certbot** для продакшена
- **Vercel/Netlify** для статического хостинга

## 🔧 Разработка

### Пересборка frontend

```bash
cd SferaAI_2/frontend
npm install
npm run build

# Копируем в mini_app/public/
cd ../..
rm -rf mini_app/public/*
cp -r SferaAI_2/frontend/out/* mini_app/public/
```

### Тестирование

```bash
pytest tests/ -v
```

## 📄 Лицензия

MIT License - см. [LICENSE](LICENSE)

## 🙏 Благодарности

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [LiveKit](https://livekit.io/)  
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime)
- [Next.js](https://nextjs.org/)

## 📞 Поддержка

Создайте Issue или обратитесь к администратору бота.

---

**Version:** 3.0 (Sfera AI Integration) | **Last Update:** December 2025
