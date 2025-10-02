import os
import logging
from dotenv import load_dotenv

# --- ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ---
load_dotenv()

# --- ВАЖНЫЕ НАСТРОЙКИ ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "SferaTC_bot")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))

# --- ДОБАВЬТЕ ЭТУ СТРОКУ ---
DATABASE_URL = os.getenv("DATABASE_URL")
# -----------------------------

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- ССЫЛКИ ---
GEM_BOT_1_URL = "https://chatgpt.com/g/g-68d9b0f1d07c8191bba533ecfb9d1689-sferatc-lessons"
AI_PSYCHOLOGIST_URL = "https://chatgpt.com/g/g-68bb703f9a3881918d51f97375d7d128-sferatc-ai"
GEM_BOT_2_URL = "https://g-2NaO34S37-sferatc-full-course"
TELEGRAM_CHANNEL_URL = "https://t.me/SferaTC"

# --- FILE_ID ДЛЯ КАРТИНОК ---
WELCOME_IMAGE_ID = os.getenv("WELCOME_IMAGE_ID")
TRAINING_IMAGE_ID = os.getenv("TRAINING_IMAGE_ID")
PSYCHOLOGIST_IMAGE_ID = os.getenv("PSYCHOLOGIST_IMAGE_ID")
CHATGPT_IMAGE_ID = os.getenv("CHATGPT_IMAGE_ID")
SUPPORT_IMAGE_ID = os.getenv("SUPPORT_IMAGE_ID")
TOOLS_IMAGE_ID = os.getenv("TOOLS_IMAGE_ID")

# --- ДАННЫЕ ДЛЯ РАЗДЕЛА "ПОЛЕЗНЫЕ ИНСТРУМЕНТЫ" ---
TOOLS_DATA = {
    'discounts': {
        'title': "💰 Скидки на комиссии",
        'intro_text': "В этом разделе собраны лучшие биржи и брокеры. Откройте счет по этим ссылкам, чтобы получить максимальные скидки и экономить на комиссиях!",
        'items': [
            { 'name': 'Крипто Брокер Tiger.com', 'callback': 'tool_tiger', 'description': 'Единая платформа для торговли на нескольких биржах. Экономьте на комиссиях, ведите автоматический дневник сделок и управляйте рисками.', 'image_id': os.getenv("TIGER_IMAGE_ID"), 'site_url': 'https://account.tiger.com/signup?referral=sferatc', 'video_url': 'https://www.youtube.com/@sferaTC' },
            { 'name': 'Крипто Брокер Vataga Crypto', 'callback': 'tool_vataga', 'description': 'Торгуйте на всех крупных биржах через одну платформу: продвинутые графики, мультиаккаунт и круглосуточная поддержка.', 'image_id': os.getenv("VATAGA_IMAGE_ID"), 'site_url': 'https://app.vataga.trading/register', 'video_url': 'https://www.youtube.com/@sferaTC' },
            { 'name': 'Крипто Брокер Whitelist', 'callback': 'tool_whitelist', 'description': 'Онлайн-офис для скальперов с мощным торговым терминалом Scalpee для ПК и большим сообществом трейдеров.', 'image_id': os.getenv("WHITELIST_IMAGE_ID"), 'site_url': 'https://passport.whitelist.capital/signup/?ref=sferatc', 'video_url': 'https://www.youtube.com/@sferaTC' }
        ]
    },
    'screeners': {'title': "📈 Скринеры", 'intro_text': "Выберите скринер:", 'items': []},
    'terminals': {'title': "🖥️ Торговые терминалы", 'intro_text': "Выберите терминал:", 'items': []},
    'ping': {'title': "⚡️ Снизить ping", 'intro_text': "Выберите сервис:", 'items': []}
}

# Проверка наличия ключевых переменных
if not all([TELEGRAM_TOKEN, ADMIN_CHAT_ID, DATABASE_URL]): # Добавили DATABASE_URL в проверку
    logger.critical("КРИТИЧЕСКАЯ ОШИБКА: Отсутствуют TELEGRAM_TOKEN, ADMIN_CHAT_ID или DATABASE_URL.")
    exit()