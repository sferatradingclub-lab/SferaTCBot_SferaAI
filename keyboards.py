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
    ["🤖 Sfera AI"],
    ["💳 Оплатить подписку"],
    ["Полезные инструменты"],
    ["Поддержка"],
]

def get_main_menu_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    current_menu = [row[:] for row in main_menu_keyboard_layout]
    webhook_url = settings.WEBHOOK_URL
    if webhook_url:
        # Sfera AI WebApp
        current_menu[0][0] = KeyboardButton(
            text="🤖 Sfera AI",
            web_app=WebAppInfo(url=webhook_url),
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

def get_tools_categories_keyboard() -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(data['title'], callback_data=f'tools_{key}')] for key, data in settings.TOOLS_DATA.items()]
    return InlineKeyboardMarkup(keyboard)

def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Статус", callback_data='admin_status')],
        [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
        [InlineKeyboardButton("📤 Сделать рассылку", callback_data='admin_broadcast')],
        [InlineKeyboardButton("👤 Управление пользователями", callback_data='admin_users')]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- КЛАВИАТУРА ДЛЯ ИИ-ПОДДЕРЖКИ ---
def get_support_llm_keyboard() -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(settings.SUPPORT_ESCALATION_BUTTON_TEXT, callback_data=settings.SUPPORT_ESCALATION_CALLBACK)]]
    return InlineKeyboardMarkup(keyboard)
