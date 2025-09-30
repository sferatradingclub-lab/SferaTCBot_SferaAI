import os
import logging
import asyncio
from datetime import datetime, time, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, WebAppInfo
from telegram.helpers import escape_markdown
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    PicklePersistence,
    JobQueue
)
from telegram.error import TelegramError
from dotenv import load_dotenv

# --- ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ---
load_dotenv()

# --- ВАЖНЫЕ НАСТРОЙКИ (ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ) ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "SferaTC_bot")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# Настройки для Webhook (обязательны для сервера)
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- ССЫЛКИ НА ВНЕШНИЕ РЕСУРСЫ И МЕДИА ---
GEM_BOT_1_URL = "https://chatgpt.com/g/g-68d9b0f1d07c8191bba533ecfb9d1689-sferatc-lessons"
AI_PSYCHOLOGIST_URL = "https://chatgpt.com/g/g-68bb703f9a3881918d51f97375d7d128-sferatc-ai"
GEM_BOT_2_URL = "https://ссылка_на_полный_курс_будет_здесь"
TELEGRAM_CHANNEL_URL = "https://t.me/SferaTC"

# --- ССЫЛКИ НА КАРТИНКИ ---
WELCOME_IMAGE_URL = "https://i.imgur.com/3mr0sbY.jpeg"
TRAINING_IMAGE_URL = "https://i.imgur.com/ouBdDqL.jpeg"
PSYCHOLOGIST_IMAGE_URL = "https://i.imgur.com/zQo6wFX.jpeg"
CHATGPT_IMAGE_URL = "https://i.imgur.com/vkfnaoi.jpeg"
SUPPORT_IMAGE_URL = "https://i.imgur.com/hO5twnQ.jpeg"
TOOLS_IMAGE_URL = "https://i.imgur.com/TljXZ62.jpeg"

# --- ДАННЫЕ ДЛЯ РАЗДЕЛА "ПОЛЕЗНЫЕ ИНСТРУМЕНТЫ" ---
TOOLS_DATA = {
    'discounts': {
        'title': "💰 Скидки на комиссии на биржах",
        'intro_text': "В данном разделе мы собрали Самые Топовые Биржи и Крипто Брокеры. Откройте счет по этим ссылкам, получите максимальные скидки и экономьте на комиссиях!",
        'items': [
            { 'name': 'Крипто Брокер Tiger.com', 'callback': 'tool_tiger', 'description': 'Единая платформа для торговли на нескольких биржах без переключения между аккаунтами. Экономьте на комиссиях, ведите автоматический дневник сделок и управляйте рисками с помощью встроенного риск-менеджера.', 'image_url': 'https://i.imgur.com/3RNcZM5.jpeg', 'site_url': 'https://account.tiger.com/signup?referral=sferatc', 'video_url': 'https://www.youtube.com/@sferaTC' },
            { 'name': 'Крипто Брокер Vataga', 'callback': 'tool_vataga', 'description': 'Торгуйте на всех крупных биржах через одну одну платформу: продвинутые графики, мультиаккаунт, скидки на комиссии и круглосуточную поддержку для активных трейдеров.', 'image_url': 'https://i.imgur.com/K2QczWr.jpeg', 'site_url': 'https://app.vataga.trading/register', 'video_url': 'https://www.youtube.com/@sferaTC' },
            { 'name': 'Крипто Брокер Whitelist', 'callback': 'tool_whitelist', 'description': 'Онлайн-офис для скальперов, предлагающий мощный торговый терминал Scalpee для ПК. Объединяет в себе личный кабинет для управления активами, гибкую настройку рабочего пространства и большое сообщество трейдеров.', 'image_url': 'https://i.imgur.com/JkzwZen.png', 'site_url': 'https://passport.whitelist.capital/', 'video_url': 'https://www.youtube.com/@sferaTC' }
        ]
    },
    'screeners': {'title': "📈 Скринеры", 'intro_text': "Выберите скринер:", 'items': []},
    'terminals': {'title': "🖥️ Торговые терминалы", 'intro_text': "Выберите терминал:", 'items': []},
    'ping': {'title': "⚡️ Снизить ping", 'intro_text': "Выберите сервис:", 'items': []}
}

# --- Клавиатура главного меню ---
main_menu_keyboard = [
    ["Пройти бесплатное обучение", "ИИ-психолог"],
    ["Полезные инструменты", "Бесплатный ChatGPT"],
    ["Поддержка"]
]

# =============================================================================
# ОСНОВНЫЕ ОБРАБОТЧИКИ
# =============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start и первый запуск бота."""
    user = update.effective_user
    
    if context.user_data.get('is_banned', False):
        return
    
    if 'first_seen' not in context.user_data:
        context.user_data['first_seen'] = datetime.now()
        logger.info(f"Новый пользователь: {user.id} ({user.full_name}) @{user.username}")

        user_fullname = escape_markdown(user.full_name or "Имя не указано", version=2)
        user_username = f"@{escape_markdown(user.username, version=2)}" if user.username else "Нет"
        
        admin_message = (
            f"👋 Новый пользователь!\n\n"
            f"Имя: {user_fullname}\n"
            f"Username: {user_username}\n"
            f"ID: `{user.id}`"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message, parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление о новом пользователе админу: {e}")

    context.user_data['last_seen'] = datetime.now()
    context.user_data['full_name'] = user.full_name
    context.user_data['username'] = user.username
    context.user_data['is_approved'] = context.user_data.get('is_approved', False)
    
    payload = " ".join(context.args)
    if payload == "trial_completed":
        response_text = (
            f"С возвращением, {user.first_name}! 🥳\n\n"
            "Ты успешно прошел вводный курс. Чтобы получить доступ к полному курсу, "
            "зарегистрируйся на бирже по нашей ссылке и пополни баланс.\n\n"
            "После этого пришли сюда свой ID пользователя с биржи для проверки."
        )
        context.user_data['state'] = 'awaiting_id_submission'
        await update.message.reply_text(response_text)
    else:
        current_menu = [row[:] for row in main_menu_keyboard]
        if str(user.id) == ADMIN_CHAT_ID:
            current_menu.append(["👑 Админка"])
        
        dynamic_main_menu = ReplyKeyboardMarkup(current_menu, resize_keyboard=True)
        
        welcome_text = (
            f"Привет, {user.first_name}!\n\n"
            "Добро пожаловать в экосистему SferaTC. Здесь ты найдешь все для успешного старта в трейдинге.\n\n"
            "Чтобы быть в курсе всех обновлений, подпишись на наш основной канал!"
        )
        keyboard = [[InlineKeyboardButton("✅ Подписаться на канал", url=TELEGRAM_CHANNEL_URL)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_photo(
            photo=WELCOME_IMAGE_URL,
            caption=welcome_text,
            reply_markup=reply_markup
        )
        
        await update.message.reply_text(
            "Выберите действие в меню ниже:",
            reply_markup=dynamic_main_menu
        )

# =============================================================================
# ОБРАБОТЧИКИ КНОПОК ГЛАВНОГО МЕНЮ
# =============================================================================

async def show_training_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает кнопку 'Пройти бесплатное обучение'."""
    if context.user_data.get('is_approved', False):
         keyboard = [[InlineKeyboardButton("Перейти к полному курсу", url=GEM_BOT_2_URL)]]
         reply_markup = InlineKeyboardMarkup(keyboard)
         await update.message.reply_text("Ты уже получил доступ к полному курсу!", reply_markup=reply_markup)
    else:
        keyboard = [[InlineKeyboardButton("🚀 Начать обучение", url=GEM_BOT_1_URL)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        caption_text = "Отлично! Наше бесплатное обучение проходит в специальном чат-боте на платформе ChatGPT."
        await update.message.reply_photo(photo=TRAINING_IMAGE_URL, caption=caption_text, reply_markup=reply_markup)

async def show_psychologist_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает кнопку 'ИИ-психолог'."""
    keyboard = [[InlineKeyboardButton("Перейти к ИИ-психологу", url=AI_PSYCHOLOGIST_URL)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    caption_text = "Наш ИИ-психолог поможет справиться со стрессом в трейдинге."
    await update.message.reply_photo(photo=PSYCHOLOGIST_IMAGE_URL, caption=caption_text, reply_markup=reply_markup)

async def show_tools_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает кнопку 'Полезные инструменты'."""
    keyboard = [
        [InlineKeyboardButton(TOOLS_DATA['discounts']['title'], callback_data='tools_discounts')],
        [InlineKeyboardButton(TOOLS_DATA['screeners']['title'], callback_data='tools_screeners')],
        [InlineKeyboardButton(TOOLS_DATA['terminals']['title'], callback_data='tools_terminals')],
        [InlineKeyboardButton(TOOLS_DATA['ping']['title'], callback_data='tools_ping')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    caption_text = "Здесь мы собрали полезные инструменты для трейдера. Выберите нужный раздел:"
    await update.message.reply_photo(photo=TOOLS_IMAGE_URL, caption=caption_text, reply_markup=reply_markup)

async def show_chatgpt_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает кнопку 'Бесплатный ChatGPT'."""
    caption_text = "Этот раздел пока в разработке. Следи за обновлениями!"
    await update.message.reply_photo(photo=CHATGPT_IMAGE_URL, caption=caption_text)

async def show_support_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает кнопку 'Поддержка'."""
    context.user_data['state'] = 'awaiting_support_message'
    await update.message.reply_photo(
        photo=SUPPORT_IMAGE_URL,
        caption="Слушаю твой вопрос. Просто отправь его следующим сообщением (можно текст, фото, видео или голосовое)."
    )

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает кнопку '👑 Админка'."""
    if str(update.effective_user.id) == ADMIN_CHAT_ID:
        admin_keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
            [InlineKeyboardButton("📤 Сделать рассылку", callback_data='admin_broadcast')],
            [InlineKeyboardButton("👤 Управление пользователями", callback_data='admin_users')]
        ]
        reply_markup = InlineKeyboardMarkup(admin_keyboard)
        await update.message.reply_text("Добро пожаловать в админ-панель:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Извините, эта команда вам недоступна.")


# =============================================================================
# ОБРАБОТЧИК ОСТАЛЬНЫХ СООБЩЕНИЙ (ПОДДЕРЖКА, ЗАЯВКИ И Т.Д.)
# =============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает все сообщения, которые не являются командами или кнопками меню."""
    user = update.effective_user

    if context.user_data.get('is_banned', False):
        return
        
    context.user_data['last_seen'] = datetime.now()
    
    admin_state = context.user_data.get('admin_state')
    user_state = context.user_data.get('state')
    
    # --- ОБРАБОТКА СООБЩЕНИЙ В ПОДДЕРЖКУ ---
    if user_state == 'awaiting_support_message' and str(user.id) != ADMIN_CHAT_ID:
        context.user_data['state'] = None 
        
        forwarded_message = await context.bot.forward_message(
            chat_id=ADMIN_CHAT_ID,
            from_chat_id=user.id,
            message_id=update.message.message_id
        )

        await update.message.reply_text("Спасибо, ваше сообщение отправлено в поддержку. Мы скоро ответим.")

        user_fullname = escape_markdown(user.full_name or "Имя не указано", version=2)
        user_username = f"@{escape_markdown(user.username, version=2)}" if user.username else "Нет"

        admin_info_text = (
            f"❗️ Новый вопрос в поддержку от пользователя *{user_fullname}* \\({user_username}\\)\\.\n"
            f"User ID: `{user.id}`\n\n"
            f"Чтобы ответить на это конкретное сообщение, нажмите кнопку ниже или используйте функцию 'Ответить' на пересланное сообщение\\."
        )
        
        reply_button = [[
            InlineKeyboardButton(
                "💬 Ответить пользователю", 
                callback_data=f'user_reply_{user.id}_{forwarded_message.message_id}'
            )
        ]]
        
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_info_text,
            reply_markup=InlineKeyboardMarkup(reply_button),
            parse_mode='MarkdownV2'
        )
        return

    # --- ОБРАБОТКА ОТВЕТА АДМИНА ---
    if str(user.id) == ADMIN_CHAT_ID and admin_state == 'users_awaiting_dm':
        target_user_id = context.user_data.get('dm_target_user_id')
        if target_user_id:
            try:
                message_id_to_reply = context.user_data.pop('reply_to_message_id', None)
                
                await context.bot.copy_message(
                    chat_id=target_user_id,
                    from_chat_id=ADMIN_CHAT_ID,
                    message_id=update.message.message_id,
                    reply_to_message_id=message_id_to_reply
                )
                
                await update.message.reply_text("✅ Сообщение успешно отправлено!")

            except TelegramError as e:
                logger.error(f"Не удалось отправить DM пользователю {target_user_id}: {e.message}")
                await update.message.reply_text(f"❌ Не удалось отправить сообщение. Ошибка: {e.message}")
        
        context.user_data['admin_state'] = None
        context.user_data.pop('dm_target_user_id', None)
        return

    # --- ОБРАБОТКА ЗАЯВКИ НА ВЕРИФИКАЦИЮ ---
    if user_state == 'awaiting_id_submission' and str(user.id) != ADMIN_CHAT_ID:
        text = update.message.text or ""
        context.user_data['awaiting_verification'] = True
        context.user_data['state'] = None

        logger.info(f"Получена заявка от user_id: {user.id} ({user.full_name}) с текстом: {text}")
        safe_full_name = escape_markdown(user.full_name, version=2)
        safe_username = escape_markdown(user.username or 'none', version=2)
        safe_text = escape_markdown(text, version=2)
        
        message_to_admin = (
            f"❗️ Новая заявка на верификацию\\!\n\n"
            f"От пользователя: {safe_full_name} (@{safe_username})\n"
            f"User ID: `{user.id}`\n"
            f"Присланный текст/ID: `{safe_text}`\n\n"
            f"Для одобрения, используйте админ\\-панель или команду:\n"
            f"`/approve {user.id}`"
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message_to_admin, parse_mode='MarkdownV2')
        await update.message.reply_text("Спасибо! Твоя заявка принята на ручную проверку. Обычно это занимает не более часа.")
        return

    # --- ОБРАБОТКА СООБЩЕНИЙ ДЛЯ РАССЫЛКИ ---
    if str(user.id) == ADMIN_CHAT_ID and admin_state == 'broadcast_awaiting_message':
        context.user_data['broadcast_message_id'] = update.message.message_id
        
        await context.bot.copy_message(
            chat_id=ADMIN_CHAT_ID,
            from_chat_id=ADMIN_CHAT_ID,
            message_id=update.message.message_id
        )
        
        confirmation_keyboard = [
            [InlineKeyboardButton("✅ Да, отправить всем", callback_data='broadcast_send')],
            [InlineKeyboardButton("❌ Отмена", callback_data='broadcast_cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(confirmation_keyboard)
        await update.message.reply_text("Вот так будет выглядеть ваше сообщение. Все верно?", reply_markup=reply_markup)
        
        context.user_data['admin_state'] = 'broadcast_awaiting_confirmation'
        return
        
    # --- ОБРАБОТКА ПОИСКА ПОЛЬЗОВАТЕЛЯ В АДМИНКЕ ---
    if str(user.id) == ADMIN_CHAT_ID and admin_state == 'users_awaiting_id':
        target_id_str = update.message.text
        context.user_data['admin_state'] = None
        
        found_user_id = None
        if target_id_str.isdigit():
            found_user_id = int(target_id_str)
            if found_user_id not in context.application.user_data:
                found_user_id = None
        else:
            cleaned_username = target_id_str.replace('@', '').lower()
            for user_id_from_db, user_data_from_db in context.application.user_data.items():
                if user_data_from_db.get('username', '').lower() == cleaned_username:
                    found_user_id = user_id_from_db
                    break
        
        if found_user_id:
            await display_user_card(update, context, found_user_id)
        else:
            await update.message.reply_text(f"❌ Пользователь '{target_id_str}' не найден.")
        return
    

# =============================================================================
# ОБРАБОТЧИКИ ИНЛАЙН-КНОПОК (CALLBACKS)
# =============================================================================

async def tools_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (код этой функции остается без изменений) ...

async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (код этой функции остается без изменений) ...

async def broadcast_confirmation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (код этой функции остается без изменений) ...

async def user_actions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает все действия с пользователями из админки."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split('_')
    action = parts[1]
    user_id = int(parts[2])
    
    user_data = context.application.user_data.get(user_id, {})

    # НОВЫЙ БЛОК ДЛЯ ОТВЕТА НА СООБЩЕНИЕ ИЗ ПОДДЕРЖКИ
    if action == "reply":
        reply_to_msg_id = int(parts[3]) if len(parts) > 3 else None
        
        context.user_data['admin_state'] = 'users_awaiting_dm'
        context.user_data['dm_target_user_id'] = user_id
        context.user_data['reply_to_message_id'] = reply_to_msg_id
        
        await query.edit_message_text(f"Введите ответ для пользователя {user_id}:")
        return

    if action == "approve":
        user_data['is_approved'] = True
        user_data['approval_date'] = datetime.now()
        user_data['awaiting_verification'] = False
        logger.info(f"Админ ({query.from_user.id}) одобрил пользователя {user_id} через карточку")
        await context.bot.send_message(chat_id=user_id, text="🎉 Поздравляем! Администратор одобрил вашу заявку.")
        await display_user_card(update, context, user_id)
        
    elif action == "revoke":
        user_data['is_approved'] = False
        user_data.pop('approval_date', None)
        logger.info(f"Админ ({query.from_user.id}) отозвал одобрение у пользователя {user_id}")
        await context.bot.send_message(chat_id=user_id, text="❗️Ваш доступ к полному курсу был отозван администратором.")
        await display_user_card(update, context, user_id)
        
    elif action == "message":
        context.user_data['admin_state'] = 'users_awaiting_dm'
        context.user_data['dm_target_user_id'] = user_id
        
        target_user_data = context.application.user_data.get(user_id, {})
        target_username = target_user_data.get('username')
        display_name = f"@{target_username}" if target_username else target_user_data.get('full_name', user_id)
        
        context.user_data.pop('reply_to_message_id', None)
        
        await query.edit_message_text(f"Введите сообщение для пользователя {display_name}:")

    elif action == "block":
        confirm_keyboard = [
            [InlineKeyboardButton("ДА, заблокировать", callback_data=f'user_blockconfirm_{user_id}')],
            [InlineKeyboardButton("Отмена", callback_data=f'user_showcard_{user_id}')]
        ]
        await query.edit_message_text(f"Вы уверены, что хотите заблокировать пользователя {user_id}?", reply_markup=InlineKeyboardMarkup(confirm_keyboard))
    
    elif action == "blockconfirm":
        user_data['is_banned'] = True
        logger.info(f"Админ ({query.from_user.id}) заблокировал пользователя {user_id}")
        await query.answer("Пользователь заблокирован.", show_alert=True)
        await display_user_card(update, context, user_id)
        
    elif action == "unblock":
        user_data.pop('is_banned', None)
        logger.info(f"Админ ({query.from_user.id}) разблокировал пользователя {user_id}")
        await query.answer("Пользователь разблокирован.", show_alert=True)
        await display_user_card(update, context, user_id)
        
    elif action == "showcard":
        await display_user_card(update, context, user_id)


# =============================================================================
# АДМИН-КОМАНДЫ И ФУНКЦИИ
# =============================================================================

async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (код этой функции остается без изменений) ...

async def reset_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (код этой функции остается без изменений) ...

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None, period="all") -> None:
    # ... (код этой функции остается без изменений) ...

async def run_broadcast(context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (код этой функции остается без изменений) ...

async def daily_stats_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (код этой функции остается без изменений) ...

async def display_user_card(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    # ... (код этой функции остается без изменений) ...


# =============================================================================
# ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА
# =============================================================================

def main() -> None:
    """Главная функция, которая собирает и запускает бота."""
    # Проверка наличия обязательных переменных окружения
    if not all([TELEGRAM_TOKEN, ADMIN_CHAT_ID]):
        error_message = "КРИТИЧЕСКАЯ ОШИБКА: Отсутствуют переменные окружения TELEGRAM_TOKEN или ADMIN_CHAT_ID."
        logger.critical(error_message)
        raise ValueError(error_message)

    persistence = PicklePersistence(filepath="bot_data.pickle")
    
    application = Application.builder().token(TELEGRAM_TOKEN).persistence(persistence).build()

    # --- РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ---
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("approve", approve_user))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("reset_user", reset_user))
    
    # Нажатия на инлайн-кнопки
    application.add_handler(CallbackQueryHandler(user_actions_handler, pattern='^user_'))
    application.add_handler(CallbackQueryHandler(tools_menu_handler, pattern='^tool'))
    application.add_handler(CallbackQueryHandler(admin_menu_handler, pattern='^admin_'))
    application.add_handler(CallbackQueryHandler(broadcast_confirmation_handler, pattern='^broadcast_'))

    # КНОПКИ ГЛАВНОГО МЕНЮ (по точному совпадению текста)
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^Пройти бесплатное обучение$'), show_training_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^ИИ-психолог$'), show_psychologist_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^Полезные инструменты$'), show_tools_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^Бесплатный ChatGPT$'), show_chatgpt_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^Поддержка$'), show_support_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^👑 Админка$'), show_admin_panel))

    # Обработчик для всех остальных сообщений (должен быть последним!)
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    # Задачи
    job_queue = application.job_queue
    report_time = time(0, 0)
    job_queue.run_daily(daily_stats_job, time=report_time, name="daily_stats_report")
    
    # --- ЗАПУСК БОТА ---
    if WEBHOOK_URL:
        # Режим Webhook для сервера
        url_path = TELEGRAM_TOKEN.split(':')[-1]
        webhook_full_url = f"{WEBHOOK_URL.rstrip('/')}/{url_path}"

        logger.info(f"Бот @{BOT_USERNAME} запускается через Webhook.")
        application.run_webhook(
            listen="0.0.0.0",
            port=WEBHOOK_PORT,
            url_path=url_path,
            webhook_url=webhook_full_url
        )
    else:
        # Режим Polling для локальной разработки
        logger.info(f"Бот @{BOT_USERNAME} запускается в режиме Polling.")
        application.run_polling()

if __name__ == "__main__":
    main()