from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
    WebAppInfo,
)
from config import get_settings

settings = get_settings()

# --- Клавиатура главного меню ---
main_menu_keyboard_layout = [
    ["🚀 Открыть приложение 🚀"],
    ["Пройти бесплатное обучение", "ИИ-психолог"],
    ["Полезные инструменты", "Бесплатный ChatGPT"],
    ["Поддержка"],
]

def get_main_menu_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    current_menu = [row[:] for row in main_menu_keyboard_layout]
    webhook_url = settings.WEBHOOK_URL
    if webhook_url:
        # Используем URL для Mini App, добавляя путь /mini-app/
        mini_app_url = f"{webhook_url}/mini-app/"
        current_menu[0][0] = KeyboardButton(
            text="🚀 Открыть приложение 🚀",
            web_app=WebAppInfo(url=mini_app_url),
        )
    if str(user_id) == settings.ADMIN_CHAT_ID:
        current_menu.append(["👑 Админка"])
    return ReplyKeyboardMarkup(current_menu, resize_keyboard=True)


def get_support_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура режима общения с поддержкой."""
    return ReplyKeyboardMarkup([["Вернуться в меню"]], resize_keyboard=True)

# --- Инлайн-клавиатуры ---
def get_channel_keyboard() -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton("✅ Подписаться на канал", url=settings.TELEGRAM_CHANNEL_URL)]]
    return InlineKeyboardMarkup(keyboard)

def get_training_keyboard(is_approved: bool) -> InlineKeyboardMarkup:
    if is_approved:
        return InlineKeyboardMarkup([[InlineKeyboardButton("Перейти к полному курсу", url=settings.FULL_COURSE_URL)]])
    else:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Начать обучение", url=settings.TRAINING_BOT_URL)]])

def get_psychologist_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Перейти к ИИ-психологу", url=settings.AI_PSYCHOLOGIST_URL)]])

def get_tools_categories_keyboard() -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(data['title'], callback_data=f'tools_{key}')] for key, data in settings.TOOLS_DATA.items()]
    return InlineKeyboardMarkup(keyboard)

def get_verification_links_keyboard() -> InlineKeyboardMarkup:
    discounts = settings.TOOLS_DATA.get('discounts', {}).get('items', [])
    tiger_url = next((item['site_url'] for item in discounts if 'Tiger.com' in item['name']), '#')
    vataga_url = next((item['site_url'] for item in discounts if 'Vataga Crypto' in item['name']), '#')
    whitelist_url = next((item['site_url'] for item in discounts if 'Whitelist' in item['name']), '#')
    
    keyboard = [
        [InlineKeyboardButton("Tiger.com", url=tiger_url)],
        [InlineKeyboardButton("Vataga Crypto", url=vataga_url)],
        [InlineKeyboardButton("Whitelist", url=whitelist_url)],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Статус", callback_data='admin_status')],
        [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
        [InlineKeyboardButton("📤 Сделать рассылку", callback_data='admin_broadcast')],
        [InlineKeyboardButton("👤 Управление пользователями", callback_data='admin_users')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_chatgpt_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру для режима ChatGPT."""
    keyboard = [["Закончить диалог"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

# --- НОВАЯ КЛАВИАТУРА ДЛЯ ИИ-ПОДДЕРЖКИ ---
def get_support_llm_keyboard() -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(settings.SUPPORT_ESCALATION_BUTTON_TEXT, callback_data=settings.SUPPORT_ESCALATION_CALLBACK)]]
    return InlineKeyboardMarkup(keyboard)
