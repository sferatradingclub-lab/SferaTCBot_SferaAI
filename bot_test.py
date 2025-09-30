import os
import asyncio
from datetime import datetime, time, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.helpers import escape_markdown
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    PicklePersistence
)
from telegram.error import TelegramError

# --- ВАЖНЫЕ НАСТРОЙКИ ---
TELEGRAM_TOKEN = "8239569004:AAEdZs-WY-fbqNCdbpij67NHFszku4PRBMg"
BOT_USERNAME = "SferaTC_bot"
ADMIN_CHAT_ID = "5732209142"

# --- ССЫЛКИ НА ВНЕШНИЕ РЕСУРСЫ И МЕДИА ---
GEM_BOT_1_URL = "https://gemini.google.com/gem/13FjrFKtiWZNv4qSKbA0oDFFPXbEq4WXy?usp=sharing"
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
            {
                'name': 'Криптобиржа Binance',
                'callback': 'tool_binance',
                'description': 'Надежная и самая популярная криптобиржа с огромным выбором торговых пар. Идеально подходит как для новичков, так и для опытных трейдеров благодаря высокой ликвидности и разнообразию функций.',
                'image_url': 'https://i.imgur.com/XJDVvVJ.jpeg',
                'site_url': 'https://www.binance.com/referral/earn-together/refer-in-hotsummer/claim?hl=ru&ref=GRO_20338_R362O&utm_source=default',
                'video_url': 'https://www.youtube.com/@sferaTC'
            },
            {
                'name': 'Криптобиржа Bybit',
                'callback': 'tool_bybit',
                'description': 'Одна из лучших платформ для торговли крипто-фьючерсами. Славится своим быстрым движком, высокой ликвидностью и удобным интерфейсом для профессиональных трейдеров.',
                'image_url': 'https://i.imgur.com/3V3jjaj.png',
                'site_url': 'https://www.bybit.com/ru-RU/',
                'video_url': 'https://www.youtube.com/@sferaTC'
            },
            {
                'name': 'Крипто Брокер Tiger.com',
                'callback': 'tool_tiger',
                'description': 'Единая платформа для торговли на нескольких биржах без переключения между аккаунтами. Экономьте на комиссиях, ведите автоматический дневник сделок и управляйте рисками с помощью встроенного риск-менеджера.',
                'image_url': 'https://i.imgur.com/3V3jjaj.png',
                'site_url': 'https://broker.tiger.com/ru/',
                'video_url': 'https://www.youtube.com/@sferaTC'
            },
            {
                'name': 'Крипто Брокер Vataga',
                'callback': 'tool_vataga',
                'description': 'Торгуйте на всех крупных биржах через одну одну платформу: продвинутые графики, мультиаккаунт, скидки на комиссии и круглосуточную поддержку для активных трейдеров.',
                'image_url': 'https://i.imgur.com/K2QczWr.jpeg',
                'site_url': 'https://app.vataga.trading/register',
                'video_url': 'https://www.youtube.com/@sferaTC'
            },
            {
                'name': 'Крипто Брокер Whitelist',
                'callback': 'tool_whitelist',
                'description': 'Онлайн-офис для скальперов, предлагающий мощный торговый терминал Scalpee для ПК. Объединяет в себе личный кабинет для управления активами, гибкую настройку рабочего пространства и большое сообщество трейдеров.',
                'image_url': 'https://i.imgur.com/JkzwZen.png',
                'site_url': 'https://passport.whitelist.capital/',
                'video_url': 'https://www.youtube.com/@sferaTC'
            }
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    
    if context.user_data.get('is_banned', False):
        return
    
    if 'first_seen' not in context.user_data:
        context.user_data['first_seen'] = datetime.now()
    
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    if context.user_data.get('is_banned', False):
        return
        
    context.user_data['last_seen'] = datetime.now()
    
    admin_state = context.user_data.get('admin_state')
    user_state = context.user_data.get('state')
    
    if str(user.id) == ADMIN_CHAT_ID and admin_state == 'users_awaiting_dm':
        target_user_id = context.user_data.get('dm_target_user_id')
        if target_user_id:
            try:
                await context.bot.copy_message(
                    chat_id=target_user_id,
                    from_chat_id=ADMIN_CHAT_ID,
                    message_id=update.message.message_id
                )
                
                nav_keyboard = [[
                    InlineKeyboardButton("⬅️ К карточке пользователя", callback_data=f'user_showcard_{target_user_id}'),
                    InlineKeyboardButton("⬅️ В админку", callback_data='admin_main')
                ]]
                reply_markup = InlineKeyboardMarkup(nav_keyboard)
                
                await update.message.reply_text("✅ Сообщение успешно отправлено!", reply_markup=reply_markup)

            except TelegramError as e:
                await update.message.reply_text(f"❌ Не удалось отправить сообщение. Ошибка: {e.message}")
        
        context.user_data['admin_state'] = None
        context.user_data.pop('dm_target_user_id', None)
        return
        
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

    if user_state == 'awaiting_id_submission' and str(user.id) != ADMIN_CHAT_ID:
        text = update.message.text or ""
        context.user_data['awaiting_verification'] = True
        context.user_data['state'] = None

        print(f"Получена заявка от user_id: {user.id} с текстом: {text}")
        safe_full_name = escape_markdown(user.full_name, version=2)
        safe_username = escape_markdown(user.username or '', version=2)
        safe_text = escape_markdown(text, version=2)
        
        message_to_admin = (
            f"❗️ Новая заявка на верификацию\\!\n\n"
            f"От пользователя: {safe_full_name} (@{safe_username})\n"
            f"User ID: `{user.id}`\n"
            f"Присланный текст/ID: `{safe_text}`\n\n"
            f"Для одобрения, скопируй и выполни команду:\n"
            f"`/approve {user.id}`"
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message_to_admin, parse_mode='MarkdownV2')
        await update.message.reply_text("Спасибо! Твоя заявка принята на ручную проверку. Обычно это занимает не более часа.")
        return

    if not update.message.text:
        return
        
    text = update.message.text
    if text == "👑 Админка":
        if str(user.id) == ADMIN_CHAT_ID:
            admin_keyboard = [
                [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
                [InlineKeyboardButton("📤 Сделать рассылку", callback_data='admin_broadcast')],
                [InlineKeyboardButton("👤 Управление пользователями", callback_data='admin_users')]
            ]
            reply_markup = InlineKeyboardMarkup(admin_keyboard)
            await update.message.reply_text("Добро пожаловать в админ-панель:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("Извините, эта команда вам недоступна.")
        return

    elif text == "Пройти бесплатное обучение":
        if context.user_data.get('is_approved', False):
             keyboard = [[InlineKeyboardButton("Перейти к полному курсу", url=GEM_BOT_2_URL)]]
             reply_markup = InlineKeyboardMarkup(keyboard)
             await update.message.reply_text("Ты уже получил доступ к полному курсу!", reply_markup=reply_markup)
        else:
            keyboard = [[InlineKeyboardButton("🚀 Начать обучение", url=GEM_BOT_1_URL)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            caption_text = "Отлично! Наше бесплатное обучение проходит в специальном чат-боте на платформе Gemini."
            await update.message.reply_photo(photo=TRAINING_IMAGE_URL, caption=caption_text, reply_markup=reply_markup)
        return

    elif text == "ИИ-психолог":
        keyboard = [[InlineKeyboardButton("Перейти к ИИ-психологу", url=AI_PSYCHOLOGIST_URL)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        caption_text = "Наш ИИ-психолог поможет справиться со стрессом в трейдинге."
        await update.message.reply_photo(photo=PSYCHOLOGIST_IMAGE_URL, caption=caption_text, reply_markup=reply_markup)
        return

    elif text == "Полезные инструменты":
        keyboard = [
            [InlineKeyboardButton(TOOLS_DATA['discounts']['title'], callback_data='tools_discounts')],
            [InlineKeyboardButton(TOOLS_DATA['screeners']['title'], callback_data='tools_screeners')],
            [InlineKeyboardButton(TOOLS_DATA['terminals']['title'], callback_data='tools_terminals')],
            [InlineKeyboardButton(TOOLS_DATA['ping']['title'], callback_data='tools_ping')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        caption_text = "Здесь мы собрали полезные инструменты для трейдера. Выберите нужный раздел:"
        await update.message.reply_photo(photo=TOOLS_IMAGE_URL, caption=caption_text, reply_markup=reply_markup)
        return

    elif text == "Бесплатный ChatGPT":
        caption_text = "Этот раздел пока в разработке. Следи за обновлениями!"
        await update.message.reply_photo(photo=CHATGPT_IMAGE_URL, caption=caption_text)
        return

    elif text == "Поддержка":
        caption_text = "Если у тебя есть вопросы, напиши их здесь, и мы скоро ответим."
        await update.message.reply_photo(photo=SUPPORT_IMAGE_URL, caption=caption_text)
        return

async def tools_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    query_data = query.data
    
    if query_data == 'tools_main':
        keyboard = [
            [InlineKeyboardButton(TOOLS_DATA['discounts']['title'], callback_data='tools_discounts')],
            [InlineKeyboardButton(TOOLS_DATA['screeners']['title'], callback_data='tools_screeners')],
            [InlineKeyboardButton(TOOLS_DATA['terminals']['title'], callback_data='tools_terminals')],
            [InlineKeyboardButton(TOOLS_DATA['ping']['title'], callback_data='tools_ping')],
        ]
        text = "Здесь мы собрали полезные инструменты для трейдера. Выберите нужный раздел:"
        media = InputMediaPhoto(media=TOOLS_IMAGE_URL, caption=text)
        try:
            await query.edit_message_media(media=media, reply_markup=InlineKeyboardMarkup(keyboard))
        except TelegramError as e:
            if not e.message.startswith("Message is not modified"):
                print(f"Error editing message media: {e}")
        return

    if query_data.startswith('tools_'):
        category_key = query_data.split('_')[1]
        category = TOOLS_DATA.get(category_key)
        
        if not category or not category['items']:
            text = "Этот раздел пока пуст, но скоро мы его наполним!"
            keyboard = [[InlineKeyboardButton("⬅️ Назад к разделам", callback_data='tools_main')]]
        else:
            text = category.get('intro_text', 'Выберите инструмент:')
            keyboard = []
            for item in category['items']:
                keyboard.append([InlineKeyboardButton(item['name'], callback_data=item['callback'])])
            keyboard.append([InlineKeyboardButton("⬅️ Назад к разделам", callback_data='tools_main')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_caption(caption=text, reply_markup=reply_markup)
        return

    if query_data.startswith('tool_'):
        selected_tool = None
        parent_category_callback = 'tools_main'
        for category_name, category_data in TOOLS_DATA.items():
            for item in category_data['items']:
                if item['callback'] == query_data:
                    selected_tool = item
                    parent_category_callback = f"tools_{category_name}"
                    break
            if selected_tool:
                break
        
        if selected_tool:
            caption = f"*{selected_tool['name']}*\n\n{selected_tool['description']}"
            keyboard = [
                [
                    InlineKeyboardButton("🔗 Открыть счет", url=selected_tool['site_url']),
                    InlineKeyboardButton("🎬 Посмотреть обзор", url=selected_tool['video_url'])
                ],
                [InlineKeyboardButton("⬅️ Назад к списку", callback_data=parent_category_callback)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            media = InputMediaPhoto(media=selected_tool['image_url'], caption=caption, parse_mode='Markdown')
            try:
                await query.edit_message_media(media=media, reply_markup=reply_markup)
            except TelegramError as e:
                if not e.message.startswith("Message is not modified"):
                    print(f"Error editing message media: {e}")
        return

async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    command = query.data
    back_to_admin_keyboard = [[InlineKeyboardButton("⬅️ Назад в админку", callback_data='admin_main')]]

    if command == 'admin_main':
        admin_keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
            [InlineKeyboardButton("📤 Сделать рассылку", callback_data='admin_broadcast')],
            [InlineKeyboardButton("👤 Управление пользователями", callback_data='admin_users')]
        ]
        reply_markup = InlineKeyboardMarkup(admin_keyboard)
        await query.edit_message_text("Добро пожаловать в админ-панель:", reply_markup=reply_markup)
        return
        
    elif command == 'admin_stats':
        stats_keyboard = [
            [InlineKeyboardButton("За сегодня", callback_data='admin_stats_today')],
            [InlineKeyboardButton("За все время", callback_data='admin_stats_all')],
            [InlineKeyboardButton("⬅️ Назад в админку", callback_data='admin_main')]
        ]
        reply_markup = InlineKeyboardMarkup(stats_keyboard)
        await query.edit_message_text("Выберите период для просмотра статистики:", reply_markup=reply_markup)
        return

    elif command == 'admin_stats_today' or command == 'admin_stats_all':
        await show_stats(update, context, query=query, period=command.split('_')[-1])

    elif command == 'admin_broadcast':
        await query.edit_message_text(
            "Режим создания рассылки активирован.\n\n"
            "Просто пришлите мне следующее сообщение (текст, фото, видео и т.д.), "
            "и я подготовлю его к отправке."
        )
        context.user_data['admin_state'] = 'broadcast_awaiting_message'

    elif command == 'admin_users':
        context.user_data['admin_state'] = 'users_awaiting_id'
        back_button = [[InlineKeyboardButton("⬅️ Назад в админку", callback_data='admin_main')]]
        await query.edit_message_text(
            "Режим управления пользователями.\n\n"
            "Отправьте мне User ID или @username пользователя, которого хотите найти.",
            reply_markup=InlineKeyboardMarkup(back_button)
        )

async def broadcast_confirmation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    command = query.data
    
    context.user_data['admin_state'] = None

    if command == 'broadcast_send':
        await query.edit_message_text("Понял. Начинаю рассылку... Оповещу вас по завершении.")
        context.job_queue.run_once(run_broadcast, 0)

    elif command == 'broadcast_cancel':
        await query.edit_message_text("Рассылка отменена.")
        context.user_data.pop('broadcast_message_id', None)

async def run_broadcast(context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_user_data = context.application.user_data.get(int(ADMIN_CHAT_ID), {})
    message_id_to_send = admin_user_data.get('broadcast_message_id')
    
    if not message_id_to_send:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="❌ Ошибка: не найдено сообщение для рассылки.")
        return

    all_user_ids = list(context.application.user_data.keys())
    
    success_count = 0
    blocked_count = 0
    error_count = 0

    for user_id in all_user_ids:
        if user_id == int(ADMIN_CHAT_ID):
            continue
            
        try:
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=ADMIN_CHAT_ID,
                message_id=message_id_to_send
            )
            success_count += 1
        except TelegramError as e:
            if "bot was blocked by the user" in e.message:
                blocked_count += 1
            else:
                error_count += 1
                print(f"Ошибка при отправке пользователю {user_id}: {e}")
        
        await asyncio.sleep(0.1)

    report_text = (
        f"✅ **Рассылка завершена\\!**\n\n"
        f"• Успешно отправлено: *{success_count}*\n"
        f"• Заблокировали бота: *{blocked_count}*\n"
        f"• Другие ошибки: *{error_count}*"
    )
    
    back_to_admin_keyboard = [[InlineKeyboardButton("⬅️ Назад в админку", callback_data='admin_main')]]
    reply_markup = InlineKeyboardMarkup(back_to_admin_keyboard)
    
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=report_text, parse_mode='MarkdownV2', reply_markup=reply_markup)
    
    admin_user_data.pop('broadcast_message_id', None)
    admin_user_data.pop('admin_state', None)

async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return
    try:
        user_id_to_approve = int(context.args[0])
        user_data = context.application.user_data[user_id_to_approve]
        user_data['is_approved'] = True
        user_data['approval_date'] = datetime.now()
        user_data['awaiting_verification'] = False
        
        await update.message.reply_text(f"✅ Пользователь {user_id_to_approve} успешно одобрен.")
        keyboard = [[InlineKeyboardButton("🎉 Перейти к полному курсу!", url=GEM_BOT_2_URL)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=user_id_to_approve,
            text="🎉 Поздравляем! Ваша заявка одобрена! Теперь вам доступен полный курс.",
            reply_markup=reply_markup
        )
    except (IndexError, ValueError):
        await update.message.reply_text("Ошибка! Используйте формат: /approve <user_id>")
    except KeyError:
        await update.message.reply_text(f"Ошибка! Пользователь с ID {context.args[0]} не найден в базе данных бота.")

async def reset_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return
    try:
        user_id_to_reset = int(context.args[0])
        if user_id_to_reset in context.application.user_data:
            context.application.user_data[user_id_to_reset].pop('awaiting_verification', None)
            await update.message.reply_text(f"Статус 'ожидает верификации' для пользователя {user_id_to_reset} сброшен.")
        else:
            await update.message.reply_text(f"Пользователь {user_id_to_reset} не найден.")
    except (IndexError, ValueError):
        await update.message.reply_text("Ошибка! Используй формат: /reset_user <user_id>")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None, period="all") -> None:
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        if not query:
             await update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return
        
    today = datetime.now().date()
    
    if period == "today":
        new_users_today = 0
        approved_users_today = 0
        active_today = 0
        for data in context.application.user_data.values():
            if data.get('first_seen') and data['first_seen'].date() == today:
                new_users_today += 1
            if data.get('approval_date') and data['approval_date'].date() == today:
                approved_users_today += 1
            if data.get('last_seen') and data['last_seen'].date() == today:
                active_today += 1
        
        awaiting_verification = sum(1 for data in context.application.user_data.values() if data.get('awaiting_verification'))
        
        stats_text = (
            f"📊 *Статистика за сегодня*\n\n"
            f"➕ Новых пользователей: *{new_users_today}*\n"
            f"🏃‍♂️ Активных пользователей: *{active_today}*\n"
            f"✅ Одобрено заявок: *{approved_users_today}*\n"
            f"⏳ Ожидает верификации: *{awaiting_verification}*"
        )
    else: # all time
        total_users = len(context.application.user_data)
        approved_users = sum(1 for data in context.application.user_data.values() if data.get('is_approved'))
        awaiting_verification = sum(1 for data in context.application.user_data.values() if data.get('awaiting_verification'))
        
        stats_text = (
            f"📊 *Статистика за все время*\n\n"
            f"👤 Всего пользователей: *{total_users}*\n"
            f"✅ Всего одобренных: *{approved_users}*\n"
            f"⏳ Ожидает верификации: *{awaiting_verification}*"
        )

    back_to_stats_keyboard = [[InlineKeyboardButton("⬅️ Назад к выбору периода", callback_data='admin_stats')]]
    
    if query:
        await query.edit_message_text(stats_text, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(back_to_stats_keyboard))
    else:
        await update.message.reply_text(stats_text, parse_mode='MarkdownV2')

async def daily_stats_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    yesterday = datetime.now().date() - timedelta(days=1)
    
    new_users_yesterday = 0
    approved_yesterday = 0
    
    for data in context.application.user_data.values():
        if data.get('first_seen') and data['first_seen'].date() == yesterday:
            new_users_yesterday += 1
        if data.get('approval_date') and data['approval_date'].date() == yesterday:
            approved_yesterday += 1

    report_text = (
        f"🗓️ *Ежедневный отчет за {yesterday.strftime('%d.%m.%Y')}*\n\n"
        f"➕ Новых пользователей: *{new_users_yesterday}*\n"
        f"✅ Одобрено пользователей: *{approved_yesterday}*"
    )
    
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=report_text, parse_mode='MarkdownV2')

async def display_user_card(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    user_data = context.application.user_data.get(user_id, {})
    
    status = "Новый"
    if user_data.get('is_banned'):
        status = "🚫 Заблокирован"
    elif user_data.get('awaiting_verification'):
        status = "⏳ Ожидает верификации"
    elif user_data.get('is_approved'):
        status = "✅ Одобрен"

    first_seen_dt = user_data.get('first_seen')
    last_seen_dt = user_data.get('last_seen')
    
    first_seen = first_seen_dt.strftime('%d.%m.%Y %H:%M').replace('.', '\\.') if first_seen_dt else 'Неизвестно'
    last_seen = last_seen_dt.strftime('%d.%m.%Y %H:%M').replace('.', '\\.') if last_seen_dt else 'Неизвестно'
    
    safe_full_name = escape_markdown(user_data.get('full_name', 'Неизвестно'), version=2)
    safe_username = escape_markdown(user_data.get('username', 'Нет'), version=2)

    card_text = (
        f"👤 *Карточка пользователя*\n\n"
        f"*ID:* `{user_id}`\n"
        f"*Имя:* {safe_full_name}\n"
        f"*Username:* @{safe_username}\n\n"
        f"*Статус:* {status}\n"
        f"*Первый визит:* {first_seen}\n"
        f"*Последняя активность:* {last_seen}"
    )
    
    action_buttons = []
    if user_data.get('awaiting_verification'):
        action_buttons.append(InlineKeyboardButton("✅ Одобрить", callback_data=f'user_approve_{user_id}'))
    elif user_data.get('is_approved'):
        action_buttons.append(InlineKeyboardButton("❌ Отозвать одобрение", callback_data=f'user_revoke_{user_id}'))

    if user_data.get('is_banned'):
        action_buttons.append(InlineKeyboardButton("✅ Разблокировать", callback_data=f'user_unblock_{user_id}'))
    else:
        if user_id != int(ADMIN_CHAT_ID):
            action_buttons.append(InlineKeyboardButton("🚫 Заблокировать", callback_data=f'user_block_{user_id}'))

    message_button = [InlineKeyboardButton("💬 Написать сообщение", callback_data=f'user_message_{user_id}')]

    keyboard = []
    if action_buttons:
        keyboard.append(action_buttons)
    keyboard.append(message_button)
    keyboard.append([
        InlineKeyboardButton("⬅️ Новый поиск", callback_data='admin_users'),
        InlineKeyboardButton("⬅️ В админку", callback_data='admin_main')
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(card_text, parse_mode='MarkdownV2', reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=card_text, parse_mode='MarkdownV2', reply_markup=reply_markup)

async def user_actions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    parts = query.data.split('_')
    action = parts[1]
    user_id = int(parts[2])
    
    user_data = context.application.user_data.get(user_id, {})

    if action == "approve":
        user_data['is_approved'] = True
        user_data['approval_date'] = datetime.now()
        user_data['awaiting_verification'] = False
        await context.bot.send_message(chat_id=user_id, text="🎉 Поздравляем! Администратор одобрил вашу заявку.")
        await display_user_card(update, context, user_id)
        
    elif action == "revoke":
        user_data['is_approved'] = False
        user_data.pop('approval_date', None)
        await context.bot.send_message(chat_id=user_id, text="❗️Ваш доступ к полному курсу был отозван администратором.")
        await display_user_card(update, context, user_id)
        
    elif action == "message":
        context.user_data['admin_state'] = 'users_awaiting_dm'
        context.user_data['dm_target_user_id'] = user_id
        
        target_user_data = context.application.user_data.get(user_id, {})
        target_username = target_user_data.get('username')
        display_name = f"@{target_username}" if target_username else target_user_data.get('full_name', user_id)
        
        await query.edit_message_text(f"Введите сообщение для пользователя {display_name}:")

    elif action == "block":
        confirm_keyboard = [
            [InlineKeyboardButton("ДА, заблокировать", callback_data=f'user_blockconfirm_{user_id}')],
            [InlineKeyboardButton("Отмена", callback_data=f'user_showcard_{user_id}')]
        ]
        await query.edit_message_text(f"Вы уверены, что хотите заблокировать пользователя {user_id}?", reply_markup=InlineKeyboardMarkup(confirm_keyboard))
    
    elif action == "blockconfirm":
        user_data['is_banned'] = True
        await query.answer("Пользователь заблокирован.", show_alert=True)
        await display_user_card(update, context, user_id)
        
    elif action == "unblock":
        user_data.pop('is_banned', None)
        await query.answer("Пользователь разблокирован.", show_alert=True)
        await display_user_card(update, context, user_id)
        
    elif action == "showcard":
        await display_user_card(update, context, user_id)

def main() -> None:
    persistence = PicklePersistence(filepath="bot_data.pickle")
    application = Application.builder().token(TELEGRAM_TOKEN).persistence(persistence).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("approve", approve_user))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("reset_user", reset_user))
    
    application.add_handler(CallbackQueryHandler(user_actions_handler, pattern='^user_'))
    application.add_handler(CallbackQueryHandler(tools_menu_handler, pattern='^tool'))
    application.add_handler(CallbackQueryHandler(admin_menu_handler, pattern='^admin_'))
    application.add_handler(CallbackQueryHandler(broadcast_confirmation_handler, pattern='^broadcast_'))

    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    job_queue = application.job_queue
    report_time = time(0, 0)
    job_queue.run_daily(daily_stats_job, time=report_time, name="daily_stats_report")

    print(f"Бот @{BOT_USERNAME} запущен и готов к работе...")
    print("Данные будут сохраняться в файл bot_data.pickle.")
    print("Ежедневный отчет будет отправляться в 00:00.")
    
    application.run_polling()

if __name__ == "__main__":
    main()