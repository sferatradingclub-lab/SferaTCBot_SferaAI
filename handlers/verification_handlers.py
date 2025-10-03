# handlers/verification_handlers.py
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from telegram.error import TelegramError

from config import logger, ADMIN_CHAT_ID, FULL_COURSE_URL
from keyboards import get_verification_links_keyboard
from .admin_handlers import display_user_card
from db_session import get_db
from models.crud import (
    get_user, set_awaiting_verification, approve_user_in_db,
    reject_user_in_db, revoke_user_in_db, ban_user_in_db
)

async def start_verification_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with get_db() as db:
        set_awaiting_verification(db, user.id, True)

    text = (
        f"С возвращением, {user.first_name}! Поздравляем с прохождением первых трех уроков нашего курса «Путь трейдера»! 🥳\n\n"
        "Чтобы поддержать наш проект и получить доступ к остальным 27 урокам, просто зарегистрируйся у одного из наших брокеров-партнеров по ссылке ниже.\n\n"
        "Ты получишь отличные бонусы и скидки на комиссии, а мы будем делать для тебя следующие уроки и другие полезности. ❤️\n\n"
        "После регистрации через нашу ссылку просто отправь сюда свой ID пользователя из личного кабинета. Мы занесём тебя в наш лист рефералов и откроем доступ к следующим урокам курса 🚀"
    )

    await update.message.reply_text(text, reply_markup=get_verification_links_keyboard())

async def handle_id_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text or ""
    with get_db() as db:
        set_awaiting_verification(db, user.id, True)  # Устанавливаем флаг, что заявка подана

    if 'verification_requests' not in context.bot_data:
        context.bot_data['verification_requests'] = {}
    context.bot_data['verification_requests'][user.id] = {'text': text, 'message_id': update.message.message_id}

    logger.info(f"Получена заявка от user_id: {user.id} ({user.full_name}) с ID биржи: {text}")

    safe_full_name = escape_markdown(user.full_name or "Имя не указано", version=2)
    safe_username = escape_markdown(user.username or 'none', version=2)
    safe_text = escape_markdown(text, version=2)

    message_to_admin = (f"❗️ Новая заявка на верификацию\\!\n\nОт: {safe_full_name} \\(@{safe_username}\\)\nUser ID: `{user.id}`\nID биржи: `{safe_text}`")

    keyboard = [[
        InlineKeyboardButton("✅ Одобрить", callback_data=f'user_approve_{user.id}'),
        InlineKeyboardButton("❌ Отклонить", callback_data=f'user_reject_{user.id}'),
        InlineKeyboardButton("💬 Написать", callback_data=f'user_message_{user.id}')
    ]]

    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message_to_admin, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))
    except TelegramError as e:
        logger.error(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось отправить заявку админу ({ADMIN_CHAT_ID}). Причина: {e.message}.")

    await update.message.reply_text("Спасибо! Твоя заявка принята на ручную проверку. Обычно это занимает не более часа.")

async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data['state'] = None
    context.user_data.pop('support_llm_history', None) # Очищаем историю ИИ-чата
    await update.message.reply_text("Спасибо, ваше сообщение отправлено в поддержку. Мы скоро ответим.")

    try:
        copied_message = await context.bot.copy_message(chat_id=ADMIN_CHAT_ID, from_chat_id=user.id, message_id=update.message.message_id)

        user_fullname = escape_markdown(user.full_name or "Имя не указано", version=2)
        user_username = f"@{escape_markdown(user.username, version=2)}" if user.username else "Нет"

        with get_db() as db:
            db_user = get_user(db, user.id)
            is_awaiting_verification = db_user.awaiting_verification if db_user else False

        if is_awaiting_verification:
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

async def user_actions_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split('_')
    action = parts[1]
    user_id = int(parts[2])

    with get_db() as db:
        db_user = get_user(db, user_id)
        display_name = f"@{db_user.username}" if db_user and db_user.username else f"ID: {user_id}"

        original_message = ""
        if query.message and query.message.text_markdown_v2:
            original_message = query.message.text_markdown_v2
        elif query.message and query.message.text:
            original_message = escape_markdown(query.message.text, version=2)

        if action == "approve":
            approve_user_in_db(db, user_id)
            logger.info(f"Админ ({query.from_user.id}) одобрил заявку {user_id}")
            try:
                await context.bot.send_message(chat_id=user_id, text="🎉 Поздравляем! Ваша заявка одобрена! Теперь вам доступен полный курс.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎉 Перейти к полному курсу!", url=FULL_COURSE_URL)]]))
            except TelegramError as e:
                logger.error(f"Не удалось отправить уведомление об одобрении пользователю {user_id}: {e.message}")
            await query.edit_message_text(f"{original_message}\n\n*Статус: ✅ Одобрено*", parse_mode='MarkdownV2')

        elif action == "reject":
            reject_user_in_db(db, user_id)
            logger.info(f"Админ ({query.from_user.id}) отклонил заявку {user_id}")
            rejection_text = "К сожалению, ваша заявка была отклонена. Возможно, произошла ошибка. Если у вас есть вопросы, напишите в поддержку."
            support_button = [[InlineKeyboardButton("✍️ Написать в поддержку", callback_data="support_from_rejection")]]
            try:
                await context.bot.send_message(chat_id=user_id, text=rejection_text, reply_markup=InlineKeyboardMarkup(support_button))
            except TelegramError as e:
                logger.error(f"Не удалось отправить уведомление об отклонении пользователю {user_id}: {e.message}")
            await query.edit_message_text(f"{original_message}\n\n*Статус: ❌ Отклонено*", parse_mode='MarkdownV2')

        elif action == "revoke":
            revoke_user_in_db(db, user_id)
            logger.info(f"Админ ({query.from_user.id}) отозвал одобрение для {user_id}")
            await query.answer("Одобрение отозвано.")

        elif action in ["reply", "message"]:
            context.user_data['admin_state'] = 'users_awaiting_dm'
            context.user_data['dm_target_user_id'] = user_id
            if action == "reply":
                context.user_data['reply_to_message_id'] = int(parts[3]) if len(parts) > 3 else None
            await query.edit_message_text(f"Введите ответ для пользователя {display_name}:")

        elif action == "block":
            await query.edit_message_text(f"Вы уверены, что хотите заблокировать {display_name}?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ДА, заблокировать", callback_data=f'user_blockconfirm_{user_id}')], [InlineKeyboardButton("Отмена", callback_data=f'user_showcard_{user_id}')]]))

        elif action == "blockconfirm":
            ban_user_in_db(db, user_id, True)
            logger.info(f"Админ ({query.from_user.id}) заблокировал {user_id}")
            await query.answer("Пользователь заблокирован.", show_alert=True)

        elif action == "unblock":
            ban_user_in_db(db, user_id, False)
            logger.info(f"Админ ({query.from_user.id}) разблокировал {user_id}")
            await query.answer("Пользователь разблокирован.", show_alert=True)

    if action not in ["approve", "reject", "reply", "message", "block"]:
        await display_user_card(update, context, user_id)

async def support_rejection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data['state'] = 'awaiting_support_message'
    await query.edit_message_text("Ваша заявка была отклонена. Опишите вашу проблему или вопрос следующим сообщением, и мы постараемся помочь.")

async def support_dm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data['state'] = 'awaiting_support_message'
    await query.edit_message_text("Опишите ваш ответ для администратора. Он будет отправлен в том же диалоге.")