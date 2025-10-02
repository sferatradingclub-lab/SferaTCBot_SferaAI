from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from config import TOOLS_DATA, TELEGRAM_CHANNEL_URL, GEM_BOT_1_URL, AI_PSYCHOLOGIST_URL, GEM_BOT_2_URL

# --- Клавиатура главного меню ---
main_menu_keyboard_layout = [
    ["Пройти бесплатное обучение", "ИИ-психолог"],
    ["Полезные инструменты", "Бесплатный ChatGPT"],
    ["Поддержка"]
]

def get_main_menu_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    from config import ADMIN_CHAT_ID 
    current_menu = [row[:] for row in main_menu_keyboard_layout]
    if str(user_id) == ADMIN_CHAT_ID:
        current_menu.append(["👑 Админка"])
    return ReplyKeyboardMarkup(current_menu, resize_keyboard=True)

# --- Инлайн-клавиатуры ---
def get_channel_keyboard() -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton("✅ Подписаться на канал", url=TELEGRAM_CHANNEL_URL)]]
    return InlineKeyboardMarkup(keyboard)

def get_training_keyboard(is_approved: bool) -> InlineKeyboardMarkup:
    if is_approved:
        return InlineKeyboardMarkup([[InlineKeyboardButton("Перейти к полному курсу", url=GEM_BOT_2_URL)]])
    else:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Начать обучение", url=GEM_BOT_1_URL)]])

def get_psychologist_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Перейти к ИИ-психологу", url=AI_PSYCHOLOGIST_URL)]])

def get_tools_categories_keyboard() -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(data['title'], callback_data=f'tools_{key}')] for key, data in TOOLS_DATA.items()]
    return InlineKeyboardMarkup(keyboard)

def get_verification_links_keyboard() -> InlineKeyboardMarkup:
    discounts = TOOLS_DATA.get('discounts', {}).get('items', [])
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
        [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
        [InlineKeyboardButton("📤 Сделать рассылку", callback_data='admin_broadcast')],
        [InlineKeyboardButton("👤 Управление пользователями", callback_data='admin_users')]
    ]
    return InlineKeyboardMarkup(keyboard)