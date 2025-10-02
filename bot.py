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
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))

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

# --- ССЫЛКИ И FILE_ID ---
GEM_BOT_1_URL = "https://chatgpt.com/g/g-68d9b0f1d07c8191bba533ecfb9d1689-sferatc-lessons"
AI_PSYCHOLOGIST_URL = "https://chatgpt.com/g/g-68bb703f9a3881918d51f97375d7d128-sferatc-ai"
GEM_BOT_2_URL = "https://g-2NaO34S37-sferatc-full-course"
TELEGRAM_CHANNEL_URL = "https://t.me/SferaTC"

# --- FILE_ID ДЛЯ КАРТИНОК (ЗАГРУЖАЮТСЯ ИЗ .env) ---
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

# --- Клавиатура главного меню ---
main_menu_keyboard = [
    ["Пройти бесплатное обучение", "ИИ-психолог"],
    ["Полезные инструменты", "Бесплатный ChatGPT"],
    ["Поддержка"]
]

# =============================================================================
# РАЗДЕЛЕННЫЕ ОБРАБОТЧИКИ ДЛЯ КНОПОК ГЛАВНОГО МЕНЮ И КОМАНД
# =============================================================================

async def show_training_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет меню 'Пройти бесплатное обучение'."""
    if context.user_data.get('is_approved', False):
         await update.message.reply_text("Ты уже получил доступ к полному курсу!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Перейти к полному курсу", url=GEM_BOT_2_URL)]]))
    else:
        await update.message.reply_photo(photo=TRAINING_IMAGE_ID, caption="Наше бесплатное обучение проходит в специальном чат-боте на платформе ChatGPT.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Начать обучение", url=GEM_BOT_1_URL)]]))

async def show_psychologist_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет меню 'ИИ-психолог'."""
    await update.message.reply_photo(photo=PSYCHOLOGIST_IMAGE_ID, caption="Наш ИИ-психолог поможет справиться со стрессом в трейдинге.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Перейти к ИИ-психологу", url=AI_PSYCHOLOGIST_URL)]]))

async def show_tools_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет меню 'Полезные инструменты'."""
    keyboard = [[InlineKeyboardButton(data['title'], callback_data=f'tools_{key}')] for key, data in TOOLS_DATA.items()]
    await update.message.reply_photo(photo=TOOLS_IMAGE_ID, caption="Здесь мы собрали полезные инструменты для трейдера. Выберите нужный раздел:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_chatgpt_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет меню 'Бесплатный ChatGPT'."""
    await update.message.reply_photo(photo=CHATGPT_IMAGE_ID, caption="Этот раздел пока в разработке. Следи за обновлениями!")

async def show_support_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет меню 'Поддержка'."""
    context.user_data['state'] = 'awaiting_support_message'
    await update.message.reply_photo(photo=SUPPORT_IMAGE_ID, caption="Слушаю твой вопрос. Просто отправь его следующим сообщением (можно текст, фото, видео или голосовое).")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет справочное сообщение."""
    await update.message.reply_text("Это бот образовательной экосистемы SferaTC. Используйте меню для навигации по разделам или введите команду, чтобы открыть нужный раздел.")

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает админ-панель."""
    if str(update.effective_user.id) == ADMIN_CHAT_ID:
        admin_keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
            [InlineKeyboardButton("📤 Сделать рассылку", callback_data='admin_broadcast')],
            [InlineKeyboardButton("👤 Управление пользователями", callback_data='admin_users')]
        ]
        await update.message.reply_text("Добро пожаловать в админ-панель:", reply_markup=InlineKeyboardMarkup(admin_keyboard))
    else:
        await update.message.reply_text("Извините, эта команда вам недоступна.")

# =============================================================================
# ОСНОВНЫЕ ФУНКЦИИ (START, HANDLE_MESSAGE, И Т.Д.)
# =============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if context.user_data.get('is_banned', False): return

    if 'first_seen' not in context.user_data:
        context.user_data['first_seen'] = datetime.now()
        logger.info(f"Новый пользователь: {user.id} ({user.full_name}) @{user.username}")
        
        user_fullname = escape_markdown(user.full_name or "Имя не указано", version=2)
        user_username = f"@{escape_markdown(user.username, version=2)}" if user.username else "Нет"
        admin_message = (f"👋 Новый пользователь\\!\n\nИмя: {user_fullname}\nUsername: {user_username}\nID: `{user.id}`")
        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message, parse_mode='MarkdownV2')
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление о новом пользователе админу: {e}")

    context.user_data.update({
        'last_seen': datetime.now(),
        'full_name': user.full_name,
        'username': user.username,
        'is_approved': context.user_data.get('is_approved', False)
    })
    
    payload = " ".join(context.args)
    if payload == "trial_completed":
        context.user_data['state'] = 'awaiting_id_submission'
        
        text = (
            f"С возвращением, {user.first_name}! Поздравляем с прохождением первых трех уроков нашего курса «Путь трейдера»! 🥳\n\n"
            "Чтобы поддержать наш проект и получить доступ к остальным 27 урокам, просто зарегистрируйся у одного из наших брокеров-партнеров по ссылке ниже.\n\n"
            "Ты получишь отличные бонусы и скидки на комиссии, а мы будем делать для тебя следующие уроки и другие полезности. ❤️\n\n"
            "После регистрации через нашу ссылку просто отправь сюда свой ID пользователя из личного кабинета. Мы занесём тебя в наш лист рефералов и откроем доступ к следующим урокам курса 🚀"
        )

        discounts = TOOLS_DATA.get('discounts', {}).get('items', [])
        tiger_url = next((item['site_url'] for item in discounts if 'Tiger.com' in item['name']), '#')
        vataga_url = next((item['site_url'] for item in discounts if 'Vataga Crypto' in item['name']), '#')
        whitelist_url = next((item['site_url'] for item in discounts if 'Whitelist' in item['name']), '#')

        keyboard = [
            [InlineKeyboardButton("Tiger.com", url=tiger_url)],
            [InlineKeyboardButton("Vataga Crypto", url=vataga_url)],
            [InlineKeyboardButton("Whitelist", url=whitelist_url)],
        ]
        
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        
    else:
        current_menu = [row[:] for row in main_menu_keyboard]
        if str(user.id) == ADMIN_CHAT_ID:
            current_menu.append(["👑 Админка"])
        
        keyboard = [[InlineKeyboardButton("✅ Подписаться на канал", url=TELEGRAM_CHANNEL_URL)]]
        await update.message.reply_photo(
            photo=WELCOME_IMAGE_ID,
            caption=(
                f"Привет, {user.first_name}!\n\n"
                "Добро пожаловать в экосистему SferaTC. Здесь ты найдешь все для успешного старта в трейдинге.\n\n"
                "Чтобы быть в курсе всех обновлений, подпишись на наш основной канал!"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await update.message.reply_text(
            "Выберите действие в меню ниже:",
            reply_markup=ReplyKeyboardMarkup(current_menu, resize_keyboard=True)
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if context.user_data.get('is_banned', False): return
    context.user_data['last_seen'] = datetime.now()
    
    admin_state = context.user_data.get('admin_state')
    user_state = context.user_data.get('state')
    
    if user_state == 'awaiting_support_message' and str(user.id) != ADMIN_CHAT_ID:
        context.user_data['state'] = None 
        await update.message.reply_text("Спасибо, ваше сообщение отправлено в поддержку. Мы скоро ответим.")

        try:
            copied_message = await context.bot.copy_message(chat_id=ADMIN_CHAT_ID, from_chat_id=user.id, message_id=update.message.message_id)
            
            user_fullname = escape_markdown(user.full_name or "Имя не указано", version=2)
            user_username = f"@{escape_markdown(user.username, version=2)}" if user.username else "Нет"
            
            if context.user_data.get('awaiting_verification', False):
                admin_info_text = (f"💬 Ответ от пользователя по заявке *{user_fullname}* \\({user_username}\\)\\.\nUser ID: `{user.id}`")
                admin_keyboard = [[
                    InlineKeyboardButton("✅ Одобрить", callback_data=f'user_approve_{user.id}'),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f'user_reject_{user.id}'),
                    InlineKeyboardButton("💬 Написать еще", callback_data=f'user_message_{user.id}')
                ]]
            else:
                admin_info_text = (f"❗️ Новый вопрос от *{user_fullname}* \\({user_username}\\)\\.\nUser ID: `{user.id}`")
                admin_keyboard = [[InlineKeyboardButton("💬 Ответить", callback_data=f'user_reply_{user.id}_{update.message.message_id}')]]

            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=admin_info_text,
                reply_to_message_id=copied_message.message_id,
                reply_markup=InlineKeyboardMarkup(admin_keyboard),
                parse_mode='MarkdownV2'
            )
        except TelegramError as e:
            logger.error(f"Не удалось отправить сообщение поддержки админу: {e.message}")
        return

    if str(user.id) == ADMIN_CHAT_ID and admin_state == 'users_awaiting_dm':
        target_user_id = context.user_data.pop('dm_target_user_id', None)
        context.user_data['admin_state'] = None
        if target_user_id:
            try:
                target_user_data = context.application.user_data[target_user_id]
                reply_to_id = target_user_data.get('verification_message_id')
                
                text_to_send = update.message.text
                keyboard = [[InlineKeyboardButton("✍️ Ответить в поддержку", callback_data="support_from_dm")]]
                
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=text_to_send,
                    reply_to_message_id=reply_to_id,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                await update.message.reply_text("✅ Сообщение успешно отправлено и привязано к заявке!")
            except TelegramError as e:
                logger.error(f"Не удалось отправить DM пользователю {target_user_id}: {e.message}")
                await update.message.reply_text(f"❌ Не удалось отправить сообщение. Ошибка: {e.message}")
        return

    if user_state == 'awaiting_id_submission' and str(user.id) != ADMIN_CHAT_ID:
        text = update.message.text or ""
        context.user_data['awaiting_verification'] = True
        context.user_data['verification_message_id'] = update.message.message_id
        context.user_data['state'] = None
        logger.info(f"Получена заявка от user_id: {user.id} ({user.full_name}) с ID биржи: {text}")
        
        safe_full_name = escape_markdown(user.full_name or "Имя не указано", version=2)
        safe_username = escape_markdown(user.username or 'none', version=2)
        safe_text = escape_markdown(text, version=2)
        
        message_to_admin = (f"❗️ Новая заявка на верификацию\\!\n\nОт: {safe_full_name} \\(@{safe_username}\\)\nUser ID: `{user.id}`\nID биржи: `{safe_text}`")
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Одобрить", callback_data=f'user_approve_{user.id}'),
                InlineKeyboardButton("❌ Отклонить", callback_data=f'user_reject_{user.id}'),
                InlineKeyboardButton("💬 Написать", callback_data=f'user_message_{user.id}')
            ]
        ]
        
        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message_to_admin, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))
        except TelegramError as e:
            logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось отправить заявку админу ({ADMIN_CHAT_ID}). Причина: {e.message}.")
        
        await update.message.reply_text("Спасибо! Твоя заявка принята на ручную проверку. Обычно это занимает не более часа.")
        return

    if str(user.id) == ADMIN_CHAT_ID:
        if admin_state == 'broadcast_awaiting_message':
            context.user_data['broadcast_message_id'] = update.message.message_id
            await context.bot.copy_message(chat_id=ADMIN_CHAT_ID, from_chat_id=ADMIN_CHAT_ID, message_id=update.message.message_id)
            confirmation_keyboard = [[InlineKeyboardButton("✅ Да, отправить всем", callback_data='broadcast_send')], [InlineKeyboardButton("❌ Отмена", callback_data='broadcast_cancel')]]
            await update.message.reply_text("Вот так будет выглядеть ваше сообщение. Все верно?", reply_markup=InlineKeyboardMarkup(confirmation_keyboard))
            context.user_data['admin_state'] = 'broadcast_awaiting_confirmation'
            return
        elif admin_state == 'users_awaiting_id':
            target_id_str = update.message.text
            context.user_data['admin_state'] = None
            found_user_id = None
            if target_id_str.isdigit():
                found_user_id = int(target_id_str)
                if found_user_id not in context.application.user_data: found_user_id = None
            else:
                cleaned_username = target_id_str.replace('@', '').lower()
                for uid, udata in context.application.user_data.items():
                    if udata.get('username', '').lower() == cleaned_username:
                        found_user_id = uid
                        break
            if found_user_id: await display_user_card(update, context, found_user_id)
            else: await update.message.reply_text(f"❌ Пользователь '{target_id_str}' не найден.")
            return

# =============================================================================
# ОБРАБОТЧИКИ ИНЛАЙН-КНОПОК
# =============================================================================

async def tools_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    query_data = query.data
    
    if query_data == 'tools_main':
        keyboard = [[InlineKeyboardButton(data['title'], callback_data=f'tools_{key}')] for key, data in TOOLS_DATA.items()]
        media = InputMediaPhoto(media=TOOLS_IMAGE_ID, caption="Здесь мы собрали полезные инструменты для трейдера. Выберите нужный раздел:")
        try:
            await query.edit_message_media(media=media, reply_markup=InlineKeyboardMarkup(keyboard))
        except TelegramError as e:
            if "Message is not modified" not in e.message: logger.warning(f"Error in tools_main: {e}")
        return

    if query_data.startswith('tools_'):
        category_key = query_data.split('_', 1)[1]
        category = TOOLS_DATA.get(category_key)
        
        if not category or not category.get('items'):
            text, keyboard = "Этот раздел пока пуст, но скоро мы его наполним!", [[InlineKeyboardButton("⬅️ Назад к разделам", callback_data='tools_main')]]
        else:
            text = category.get('intro_text', 'Выберите инструмент:')
            keyboard = [[InlineKeyboardButton(item['name'], callback_data=item['callback'])] for item in category['items']]
            keyboard.append([InlineKeyboardButton("⬅️ Назад к разделам", callback_data='tools_main')])

        await query.edit_message_caption(caption=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if query_data.startswith('tool_'):
        selected_tool, parent_category_callback = None, 'tools_main'
        for cat_name, cat_data in TOOLS_DATA.items():
            for item in cat_data['items']:
                if item['callback'] == query_data:
                    selected_tool, parent_category_callback = item, f"tools_{cat_name}"
                    break
            if selected_tool: break
        
        if selected_tool:
            caption = f"*{selected_tool['name']}*\n\n{selected_tool['description']}"
            keyboard = [[InlineKeyboardButton("🔗 Открыть счет", url=selected_tool['site_url']), InlineKeyboardButton("🎬 Посмотреть обзор", url=selected_tool['video_url'])], [InlineKeyboardButton("⬅️ Назад к списку", callback_data=parent_category_callback)]]
            media = InputMediaPhoto(media=selected_tool['image_id'], caption=caption, parse_mode='Markdown')
            try:
                await query.edit_message_media(media=media, reply_markup=InlineKeyboardMarkup(keyboard))
            except TelegramError as e:
                if "Message is not modified" not in e.message: logger.warning(f"Error editing tool media: {e}")

async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    command = query.data

    if command == 'admin_main':
        admin_keyboard = [[InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')], [InlineKeyboardButton("📤 Сделать рассылку", callback_data='admin_broadcast')], [InlineKeyboardButton("👤 Управление пользователями", callback_data='admin_users')]]
        await query.edit_message_text("Добро пожаловать в админ-панель:", reply_markup=InlineKeyboardMarkup(admin_keyboard))
    elif command == 'admin_stats':
        stats_keyboard = [[InlineKeyboardButton("За сегодня", callback_data='admin_stats_today')], [InlineKeyboardButton("За все время", callback_data='admin_stats_all')], [InlineKeyboardButton("⬅️ Назад в админку", callback_data='admin_main')]]
        await query.edit_message_text("Выберите период для просмотра статистики:", reply_markup=InlineKeyboardMarkup(stats_keyboard))
    elif command in ['admin_stats_today', 'admin_stats_all']:
        await show_stats(update, context, query=query, period=command.split('_')[-1])
    elif command == 'admin_broadcast':
        await query.edit_message_text("Режим создания рассылки. Пришлите следующее сообщение, и я подготовлю его к отправке.")
        context.user_data['admin_state'] = 'broadcast_awaiting_message'
    elif command == 'admin_users':
        context.user_data['admin_state'] = 'users_awaiting_id'
        await query.edit_message_text("Режим управления. Отправьте User ID или @username пользователя для поиска.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад в админку", callback_data='admin_main')]]))

async def broadcast_confirmation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    command = query.data
    context.user_data['admin_state'] = None
    if command == 'broadcast_send':
        await query.edit_message_text("Начинаю рассылку... Оповещу по завершении.")
        context.job_queue.run_once(run_broadcast, 0)
    elif command == 'broadcast_cancel':
        await query.edit_message_text("Рассылка отменена.")
        context.user_data.pop('broadcast_message_id', None)

async def user_actions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_')
    action = parts[1]
    user_id = int(parts[2])
    
    user_data = context.application.user_data.get(user_id, {})
    target_user_data = context.application.user_data.get(user_id, {})
    display_name = f"@{target_user_data.get('username')}" if target_user_data.get('username') else target_user_data.get('full_name', f"ID: {user_id}")
    
    original_message = ""
    if query.message and query.message.text_markdown_v2:
        original_message = query.message.text_markdown_v2
    elif query.message and query.message.text:
        original_message = escape_markdown(query.message.text, version=2)

    if action == "approve":
        user_data.update({'is_approved': True, 'approval_date': datetime.now(), 'awaiting_verification': False})
        logger.info(f"Админ ({query.from_user.id}) одобрил заявку {user_id}")
        try:
            await context.bot.send_message(chat_id=user_id, text="🎉 Поздравляем! Ваша заявка одобрена! Теперь вам доступен полный курс.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎉 Перейти к полному курсу!", url=GEM_BOT_2_URL)]]))
        except TelegramError as e:
            logger.error(f"Не удалось отправить уведомление об одобрении пользователю {user_id}: {e.message}")
        await query.edit_message_text(f"{original_message}\n\n*Статус: ✅ Одобрено*", parse_mode='MarkdownV2')
    
    elif action == "reject":
        user_data.pop('awaiting_verification', None)
        logger.info(f"Админ ({query.from_user.id}) отклонил заявку {user_id}")
        
        rejection_text = "К сожалению, ваша заявка была отклонена. Возможно, произошла ошибка при регистрации. Если у вас есть вопросы, вы можете написать в поддержку."
        support_button = [[InlineKeyboardButton("✍️ Написать в поддержку", callback_data="support_from_rejection")]]
        
        try:
            await context.bot.send_message(chat_id=user_id, text=rejection_text, reply_markup=InlineKeyboardMarkup(support_button))
        except TelegramError as e:
            logger.error(f"Не удалось отправить уведомление об отклонении пользователю {user_id}: {e.message}")
        await query.edit_message_text(f"{original_message}\n\n*Статус: ❌ Отклонено*", parse_mode='MarkdownV2')

    elif action == "reply":
        reply_to_msg_id = int(parts[3]) if len(parts) > 3 else None
        context.user_data.update({'admin_state': 'users_awaiting_dm', 'dm_target_user_id': user_id, 'reply_to_message_id': reply_to_msg_id})
        await query.edit_message_text(f"Введите ответ для пользователя {display_name}:")
        return
    elif action == "message":
        context.user_data.update({'admin_state': 'users_awaiting_dm', 'dm_target_user_id': user_id})
        context.user_data.pop('reply_to_message_id', None) 
        await query.edit_message_text(f"Введите сообщение для {display_name} (оно будет отправлено в ответ на его заявку):")
        return
    elif action == "block":
        await query.edit_message_text(f"Вы уверены, что хотите заблокировать {display_name}?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ДА, заблокировать", callback_data=f'user_blockconfirm_{user_id}')], [InlineKeyboardButton("Отмена", callback_data=f'user_showcard_{user_id}')]]))
        return
    elif action == "blockconfirm":
        user_data['is_banned'] = True
        logger.info(f"Админ ({query.from_user.id}) заблокировал {user_id}")
        await query.answer("Пользователь заблокирован.", show_alert=True)
    elif action == "unblock":
        user_data.pop('is_banned', None)
        logger.info(f"Админ ({query.from_user.id}) разблокировал {user_id}")
        await query.answer("Пользователь разблокирован.", show_alert=True)
    
    if action not in ["approve", "reject"]:
        await display_user_card(update, context, user_id)

async def support_rejection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data['state'] = 'awaiting_support_message'
    await query.edit_message_text("Ваша заявка была отклонена. Опишите вашу проблему или вопрос следующим сообщением, и мы постараемся помочь.")

async def support_dm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Активирует режим поддержки после нажатия на кнопку 'Ответить в поддержку' под сообщением от админа."""
    query = update.callback_query
    await query.answer()
    context.user_data['state'] = 'awaiting_support_message'
    await query.edit_message_text("Опишите ваш ответ для администратора. Он будет отправлен в том же диалоге.")

async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_user.id) != ADMIN_CHAT_ID: return
    try:
        user_id_to_approve = int(context.args[0])
        user_data = context.application.user_data[user_id_to_approve]
        user_data.update({'is_approved': True, 'approval_date': datetime.now(), 'awaiting_verification': False})
        logger.info(f"Админ ({update.effective_user.id}) одобрил {user_id_to_approve}")
        await update.message.reply_text(f"✅ Пользователь {user_id_to_approve} успешно одобрен.")
        await context.bot.send_message(chat_id=user_id_to_approve, text="🎉 Поздравляем! Ваша заявка одобрена! Теперь вам доступен полный курс.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎉 Перейти к полному курсу!", url=GEM_BOT_2_URL)]]))
    except (IndexError, ValueError):
        await update.message.reply_text("Ошибка! Используйте: /approve <user_id>")
    except KeyError:
        await update.message.reply_text(f"Ошибка! Пользователь с ID {context.args[0]} не найден.")

async def reset_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_user.id) != ADMIN_CHAT_ID: return
    try:
        user_id_to_reset = int(context.args[0])
        if user_id_to_reset in context.application.user_data:
            context.application.user_data[user_id_to_reset].clear()
            logger.info(f"Админ ({update.effective_user.id}) полностью очистил данные пользователя {user_id_to_reset}")
            await update.message.reply_text(f"✅ Данные пользователя {user_id_to_reset} полностью очищены. Теперь он считается новым.")
        else:
            await update.message.reply_text(f"Пользователь {user_id_to_reset} не найден в базе.")
    except (IndexError, ValueError):
        await update.message.reply_text("Ошибка! Используй: /reset_user <user_id>")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None, period="all") -> None:
    if str(update.effective_user.id) != ADMIN_CHAT_ID: return
    
    all_data = context.application.user_data.values()
    today = datetime.now().date()
    
    if period == "today":
        new_today = sum(1 for d in all_data if d.get('first_seen') and d['first_seen'].date() == today)
        approved_today = sum(1 for d in all_data if d.get('approval_date') and d['approval_date'].date() == today)
        active_today = sum(1 for d in all_data if d.get('last_seen') and d['last_seen'].date() == today)
        awaiting = sum(1 for d in all_data if d.get('awaiting_verification'))
        stats_text = (f"📊 *Статистика за сегодня*\n\n➕ Новых: *{new_today}*\n🏃‍♂️ Активных: *{active_today}*\n✅ Одобрено: *{approved_today}*\n⏳ Ожидает: *{awaiting}*")
    else:
        total = len(all_data)
        approved = sum(1 for d in all_data if d.get('is_approved'))
        awaiting = sum(1 for d in all_data if d.get('awaiting_verification'))
        stats_text = (f"📊 *Статистика за все время*\n\n👤 Всего: *{total}*\n✅ Одобрено: *{approved}*\n⏳ Ожидает: *{awaiting}*")

    if query:
        await query.edit_message_text(stats_text, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data='admin_stats')]]))
    else:
        await update.message.reply_text(stats_text, parse_mode='MarkdownV2')

async def run_broadcast(context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_user_data = context.application.user_data.get(int(ADMIN_CHAT_ID), {})
    message_id_to_send = admin_user_data.pop('broadcast_message_id', None)
    if not message_id_to_send:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="❌ Ошибка: не найдено сообщение для рассылки.")
        return

    user_ids = [uid for uid in context.application.user_data.keys() if uid != int(ADMIN_CHAT_ID)]
    success, blocked, error = 0, 0, 0
    logger.info(f"Начинаю рассылку для {len(user_ids)} пользователей.")
    
    for user_id in user_ids:
        try:
            await context.bot.copy_message(chat_id=user_id, from_chat_id=ADMIN_CHAT_ID, message_id=message_id_to_send)
            success += 1
        except TelegramError as e:
            if "bot was blocked" in e.message or "user is deactivated" in e.message:
                blocked += 1
            else:
                error += 1
                logger.warning(f"Ошибка рассылки пользователю {user_id}: {e}")
        await asyncio.sleep(0.1)

    report_text = (f"✅ **Рассылка завершена\\!**\n\n• Успешно: *{success}*\n• Заблокировали: *{blocked}*\n• Ошибки: *{error}*")
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=report_text, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ В админку", callback_data='admin_main')]]))

async def daily_stats_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    yesterday = (datetime.now() - timedelta(days=1)).date()
    new_yesterday = sum(1 for d in context.application.user_data.values() if d.get('first_seen') and d['first_seen'].date() == yesterday)
    approved_yesterday = sum(1 for d in context.application.user_data.values() if d.get('approval_date') and d['approval_date'].date() == yesterday)
    report_text = (f"🗓️ *Отчет за {yesterday.strftime('%d.%m.%Y')}*\n\n➕ Новых: *{new_yesterday}*\n✅ Одобрено: *{approved_yesterday}*")
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=report_text, parse_mode='MarkdownV2')

async def display_user_card(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    user_data = context.application.user_data.get(user_id, {})
    status = "🚫 Заблокирован" if user_data.get('is_banned') else "⏳ Ожидает" if user_data.get('awaiting_verification') else "✅ Одобрен" if user_data.get('is_approved') else "Новый"
    
    first_seen_str = user_data.get('first_seen').strftime('%d.%m.%Y %H:%M') if user_data.get('first_seen') else 'Неизвестно'
    last_seen_str = user_data.get('last_seen').strftime('%d.%m.%Y %H:%M') if user_data.get('last_seen') else 'Неизвестно'
    
    safe_name = escape_markdown(user_data.get('full_name', 'Неизвестно'), version=2)
    safe_user = escape_markdown(user_data.get('username', 'Нет'), version=2)

    card_text = (
        f"👤 *Карточка пользователя*\n\n"
        f"*ID:* `{user_id}`\n*Имя:* {safe_name}\n*Username:* @{safe_user}\n\n"
        f"*Статус:* {status}\n*Первый визит:* {escape_markdown(first_seen_str, version=2)}\n*Активность:* {escape_markdown(last_seen_str, version=2)}"
    )
    
    action_buttons = []
    if user_data.get('awaiting_verification'): action_buttons.append(InlineKeyboardButton("✅ Одобрить", callback_data=f'user_approve_{user_id}'))
    elif user_data.get('is_approved'): action_buttons.append(InlineKeyboardButton("❌ Отозвать", callback_data=f'user_revoke_{user_id}'))
    
    if user_id != int(ADMIN_CHAT_ID):
        if user_data.get('is_banned'): action_buttons.append(InlineKeyboardButton("✅ Разблок", callback_data=f'user_unblock_{user_id}'))
        else: action_buttons.append(InlineKeyboardButton("🚫 Заблок", callback_data=f'user_block_{user_id}'))

    keyboard = [action_buttons] if action_buttons else []
    keyboard.append([InlineKeyboardButton("💬 Написать", callback_data=f'user_message_{user_id}')])
    keyboard.append([InlineKeyboardButton("⬅️ Новый поиск", callback_data='admin_users'), InlineKeyboardButton("⬅️ В админку", callback_data='admin_main')])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(card_text, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=card_text, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))

# =============================================================================
# ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА
# =============================================================================

def main() -> None:
    """Главная функция, которая собирает и запускает бота."""
    if not all([TELEGRAM_TOKEN, ADMIN_CHAT_ID]):
        logger.critical("КРИТИЧЕСКАЯ ОШИБКА: Отсутствуют TELEGRAM_TOKEN или ADMIN_CHAT_ID.")
        return

    persistence = PicklePersistence(filepath="bot_data.pickle")
    
    application = Application.builder().token(TELEGRAM_TOKEN).persistence(persistence).build()

    # --- РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ---

    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("training", show_training_menu))
    application.add_handler(CommandHandler("psychologist", show_psychologist_menu))
    application.add_handler(CommandHandler("tools", show_tools_menu))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("chatgpt", show_chatgpt_menu))
    application.add_handler(CommandHandler("support", show_support_menu))
    
    # Команды только для админа
    application.add_handler(CommandHandler("approve", approve_user))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("reset_user", reset_user))

    # Инлайн-кнопки
    application.add_handler(CallbackQueryHandler(user_actions_handler, pattern='^user_'))
    application.add_handler(CallbackQueryHandler(tools_menu_handler, pattern='^tool'))
    application.add_handler(CallbackQueryHandler(admin_menu_handler, pattern='^admin_'))
    application.add_handler(CallbackQueryHandler(broadcast_confirmation_handler, pattern='^broadcast_'))
    application.add_handler(CallbackQueryHandler(support_rejection_handler, pattern='^support_from_rejection$'))
    application.add_handler(CallbackQueryHandler(support_dm_handler, pattern='^support_from_dm$'))

    # Кнопки главного меню
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^Пройти бесплатное обучение$'), show_training_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^ИИ-психолог$'), show_psychologist_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^Полезные инструменты$'), show_tools_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^Бесплатный ChatGPT$'), show_chatgpt_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^Поддержка$'), show_support_menu))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^👑 Админка$'), show_admin_panel))

    # Все остальные сообщения (должен быть последним!)
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    # Задачи
    application.job_queue.run_daily(daily_stats_job, time=time(0, 0), name="daily_stats_report")

    # --- ЗАПУСК БОТА ---
    if WEBHOOK_URL:
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
        logger.info(f"Бот @{BOT_USERNAME} запускается в режиме Polling.")
        application.run_polling()

if __name__ == "__main__":
    main()