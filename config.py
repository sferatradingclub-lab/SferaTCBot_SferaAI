from typing import Union
import os
import logging
from dotenv import load_dotenv
from typing import Union

# --- ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ---
load_dotenv()

DEFAULT_CHATGPT_FREE_MODELS = [
    "deepseek/deepseek-chat-v3.1:free",
    "qwen/qwen3-8b:free",
]


def ensure_free_models(models: list[str]) -> list[str]:
    """Возвращает только бесплатные модели и подставляет значения по умолчанию при необходимости."""
    logger_instance = logging.getLogger(__name__)
    free_models = [model for model in models if model and model.endswith(":free")]

    if free_models:
        return free_models

    logger_instance.warning(
        "Не найдены бесплатные модели в конфигурации. Будут использованы значения по умолчанию: %s.",
        ", ".join(DEFAULT_CHATGPT_FREE_MODELS),
    )
    return DEFAULT_CHATGPT_FREE_MODELS.copy()


# --- ВАЖНЫЕ НАСТРОЙКИ ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "SferaTC_bot")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))

# --- Настройки подключения к базе данных ---
# По умолчанию используется локальная база данных SQLite для удобства разработки.
# Для продакшена необходимо в .env файле указать DATABASE_URL для PostgreSQL.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sferatc_dev.db")

# --- Настройки для ИИ-чата через OpenRouter ---
CHATGPT_BASE_URL = "https://openrouter.ai/api/v1"
# Список бесплатных моделей OpenRouter (можно переопределить через .env, платные модели требуют положительный баланс)
_RAW_CHATGPT_MODELS = [
    os.getenv("CHATGPT_MODEL_PRIMARY", DEFAULT_CHATGPT_FREE_MODELS[0]),
    os.getenv("CHATGPT_MODEL_FALLBACK", DEFAULT_CHATGPT_FREE_MODELS[1]),
]
CHATGPT_MODELS = ensure_free_models(_RAW_CHATGPT_MODELS)
DISCARDED_PAID_MODELS = [
    model for model in _RAW_CHATGPT_MODELS if model and not model.endswith(":free")
]
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


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

if DISCARDED_PAID_MODELS:
    logger.warning(
        "Платные модели были проигнорированы и не будут использоваться: %s.",
        ", ".join(DISCARDED_PAID_MODELS),
    )

# --- ССЫЛКИ ---
TRAINING_BOT_URL = "https://chatgpt.com/g/g-68d9b0f1d07c8191bba533ecfb9d1689-sferatc-lessons"
AI_PSYCHOLOGIST_URL = "https://chatgpt.com/g/g-68bb703f9a3881918d51f97375d7d128-sferatc-ai"
FULL_COURSE_URL = "https://g-2NaO34S37-sferatc-full-course"
TELEGRAM_CHANNEL_URL = "https://t.me/SferaTC"

# --- URL АДРЕСА КАРТИНОК ---
WELCOME_IMAGE_URL = os.getenv("WELCOME_IMAGE_URL")
TRAINING_IMAGE_URL = os.getenv("TRAINING_IMAGE_URL")
PSYCHOLOGIST_IMAGE_URL = os.getenv("PSYCHOLOGIST_IMAGE_URL")
CHATGPT_IMAGE_URL = os.getenv("CHATGPT_IMAGE_URL")
SUPPORT_IMAGE_URL = os.getenv("SUPPORT_IMAGE_URL")
TOOLS_IMAGE_URL = os.getenv("TOOLS_IMAGE_URL")

# --- НОВЫЕ НАСТРОЙКИ ДЛЯ ДВУХУРОВНЕВОЙ ПОДДЕРЖКИ ---
SUPPORT_LLM_SYSTEM_PROMPT = (
    "Ты — ИИ-агент поддержки SferaTC Bot. Твоя задача — помогать пользователям решать "
    "технические и организационные вопросы, связанные с ботом и трейдингом. Будь вежливым, "
    "говори по делу, не выдумывай факты и честно признавай, если чего-то не знаешь."
)
SUPPORT_ESCALATION_BUTTON_TEXT = "Позвать администратора"
SUPPORT_ESCALATION_CALLBACK = "support_llm_escalate"
SUPPORT_LLM_HISTORY_LIMIT = 10
# ---------------------------------------------------------

def get_safe_url(url: Union[str, None], context_name: str) -> Union[str, None]:
    """Возвращает URL, если он задан, иначе логирует предупреждение."""
    if url:
        return url

    logger.warning(
        "Отсутствует URL для '%s'. Будет использован текстовый fallback.",
        context_name,
    )
    return None

# --- ДАННЫЕ ДЛЯ РАЗДЕЛА "ПОЛЕЗНЫЕ ИНСТРУМЕНТЫ" ---
TOOLS_DATA = {
    'discounts': {
        'title': "💰 Скидки на комиссии",
        'intro_text': "В этом разделе собраны лучшие биржи и брокеры. Откройте счет по этим ссылкам, чтобы получить максимальные скидки и экономить на комиссиях!",
        'items': [
            { 'name': 'Крипто Брокер Tiger.com', 'callback': 'tool_tiger', 'description': 'Единая платформа для торговли на нескольких биржах. Экономьте на комиссиях, ведите автоматический дневник сделок и управляйте рисками.', 'image_url': os.getenv("TIGER_IMAGE_URL"), 'site_url': 'https://account.tiger.com/signup?referral=sferatc', 'video_url': 'https://www.youtube.com/@sferaTC' },
            { 'name': 'Крипто Брокер Vataga Crypto', 'callback': 'tool_vataga', 'description': 'Торгуйте на всех крупных биржах через одну платформу: продвинутые графики, мультиаккаунт и круглосуточная поддержка.', 'image_url': os.getenv("VATAGA_IMAGE_URL"), 'site_url': 'https://app.vataga.trading/register', 'video_url': 'https://www.youtube.com/@sferaTC' },
            { 'name': 'Крипто Брокер Whitelist', 'callback': 'tool_whitelist', 'description': 'Онлайн-офис для скальперов с мощным торговым терминалом Scalpee для ПК и большим сообществом трейдеров.', 'image_url': os.getenv("WHITELIST_IMAGE_URL"), 'site_url': 'https://passport.whitelist.capital/signup/?ref=sferatc', 'video_url': 'https://www.youtube.com/@sferaTC' }
        ]
    },
    'screeners': {'title': "📈 Скринеры", 'intro_text': "Выберите скринер:", 'items': []},
    'terminals': {'title': "🖥️ Торговые терминалы", 'intro_text': "Выберите терминал:", 'items': []},
    'ping': {'title': "⚡️ Снизить ping", 'intro_text': "Выберите сервис:", 'items': []}
}

# Проверка обязательных настроек выполняется через ensure_required_settings().
def ensure_required_settings() -> None:
    """Убеждается, что заданы обязательные переменные окружения."""
    missing_settings = []

    if not TELEGRAM_TOKEN:
        missing_settings.append("TELEGRAM_TOKEN")
    if not ADMIN_CHAT_ID:
        missing_settings.append("ADMIN_CHAT_ID")

    if missing_settings:
        message = (
            "КРИТИЧЕСКАЯ ОШИБКА: Отсутствуют обязательные переменные окружения "
            + ", ".join(missing_settings)
            + "."
        )
        logger.critical(message)
        raise RuntimeError(message)

# Предупреждение, если используется БД для разработки
if "sqlite" in DATABASE_URL:
    logger.warning("Используется локальная база данных SQLite для разработки. Для продакшена укажите DATABASE_URL.")

# Предупреждение, если не задан ключ для ИИ-чата
if not OPENROUTER_API_KEY:
    logger.warning("OPENROUTER_API_KEY не найден. Функция 'Бесплатный ChatGPT' будет недоступна.")