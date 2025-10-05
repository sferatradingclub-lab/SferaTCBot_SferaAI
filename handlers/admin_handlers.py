import asyncio
from datetime import datetime, time, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown
from telegram.error import TelegramError

from config import logger, ADMIN_CHAT_ID, FULL_COURSE_URL
from keyboards import get_admin_panel_keyboard
from db_session import get_db
from models.crud import get_all_users, get_user, approve_user_in_db, ban_user_in_db

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_user.id) == ADMIN_CHAT_ID:
        await update.message.reply_text("Добро пожаловать в админ-панель:", reply_markup=get_admin_panel_keyboard())
    else:
        await update.message.reply_text("Извините, эта команда вам недоступна.")

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_state = context.user_data.get('admin_state')
    with get_db() as db:
        if admin_state == 'broadcast_awaiting_message':
            context.user_data['broadcast_message_id'] = update.message.message_id
            await context.bot.copy_message(chat_id=ADMIN_CHAT_ID, from_chat_id=ADMIN_CHAT_ID, message_id=update.message.message_id)
            confirmation_keyboard = [[InlineKeyboardButton("✅ Да, отправить всем", callback_data='broadcast_send')], [InlineKeyboardButton("❌ Отмена", callback_data='broadcast_cancel')]]
            await update.message.reply_text("Вот так будет выглядеть ваше сообщение. Все верно?", reply_markup=InlineKeyboardMarkup(confirmation_keyboard))
            context.user_data['admin_state'] = 'broadcast_awaiting_confirmation'

        elif admin_state == 'users_awaiting_id':
            target_id_str = update.message.text
            context.user_data['admin_state'] = None

            found_user = None
            if target_id_str.isdigit():
                found_user = get_user(db, int(target_id_str))
            else:
                cleaned_username = target_id_str.replace('@', '').lower()
                all_users = get_all_users(db)
                for user in all_users:
                    if user.username and user.username.lower() == cleaned_username:
                        found_user = user
                        break

            if found_user:
                await display_user_card(update, context, found_user.user_id)
            else:
                await update.message.reply_text(f"❌ Пользователь '{target_id_str}' не найден.")

        elif admin_state == 'users_awaiting_dm':
            target_user_id = context.user_data.pop('dm_target_user_id', None)
            reply_to_message_id = context.user_data.pop('reply_to_message_id', None)
            context.user_data['admin_state'] = None
            if target_user_id:
                text_to_send = update.message.text
                try:
                    send_kwargs = {
                        "chat_id": target_user_id,
                        "text": text_to_send,
                    }
                    if reply_to_message_id is not None:
                        send_kwargs["reply_to_message_id"] = reply_to_message_id

                    await context.bot.send_message(**send_kwargs)
                    await update.message.reply_text("✅ Сообщение успешно отправлено!")
                except TelegramError as e:
                    logger.error(f"Не удалось отправить DM пользователю {target_user_id}: {e.message}")
                    await update.message.reply_text(f"❌ Не удалось отправить сообщение. Ошибка: {e.message}")


async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    command = query.data

    if command == 'admin_main':
        await query.edit_message_text("Добро пожаловать в админ-панель:", reply_markup=get_admin_panel_keyboard())
    elif command == 'admin_stats':
        stats_keyboard = [
            [InlineKeyboardButton("За сегодня", callback_data='admin_stats_today')],
            [InlineKeyboardButton("За все время", callback_data='admin_stats_all')],
            [InlineKeyboardButton("⬅️ Назад в админку", callback_data='admin_main')]
        ]
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

async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_user.id) != ADMIN_CHAT_ID:
        return

    try:
        user_id_to_approve = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Ошибка! Используйте: /approve <user_id>")
        return

    with get_db() as db:
        db_user = approve_user_in_db(db, user_id_to_approve)
        if db_user:
            logger.info(f"Админ ({update.effective_user.id}) одобрил {user_id_to_approve}")
            await update.message.reply_text(f"✅ Пользователь {user_id_to_approve} успешно одобрен.")
            await context.bot.send_message(
                chat_id=user_id_to_approve,
                text="🎉 Поздравляем! Ваша заявка одобрена! Теперь вам доступен полный курс.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎉 Перейти к полному курсу!", url=FULL_COURSE_URL)]])
            )
        else:
            await update.message.reply_text(f"Ошибка! Пользователь с ID {user_id_to_approve} не найден.")

async def reset_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Функция сброса пользователя требует обновления для работы с БД.")


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None, period="all") -> None:
    if str(update.effective_user.id) != ADMIN_CHAT_ID: return
    
    with get_db() as db:
        all_users = get_all_users(db)

    today = datetime.now().date()
    
    if period == "today":
        new_today = sum(1 for u in all_users if u.first_seen and u.first_seen.date() == today)
        approved_today = sum(1 for u in all_users if u.approval_date and u.approval_date.date() == today)
        active_today = sum(1 for u in all_users if u.last_seen and u.last_seen.date() == today)
        awaiting = sum(1 for u in all_users if u.awaiting_verification)
        stats_text = (f"📊 *Статистика за сегодня*\n\n➕ Новых: *{new_today}*\n🏃‍♂️ Активных: *{active_today}*\n✅ Одобрено: *{approved_today}*\n⏳ Ожидает: *{awaiting}*")
    else:
        total = len(all_users)
        approved = sum(1 for u in all_users if u.is_approved)
        awaiting = sum(1 for u in all_users if u.awaiting_verification)
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

    with get_db() as db:
        all_users = get_all_users(db)
    user_ids = [u.user_id for u in all_users if u.user_id != int(ADMIN_CHAT_ID)]

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
    with get_db() as db:
        all_users = get_all_users(db)

    yesterday = (datetime.now() - timedelta(days=1)).date()
    new_yesterday = sum(1 for u in all_users if u.first_seen and u.first_seen.date() == yesterday)
    approved_yesterday = sum(1 for u in all_users if u.approval_date and u.approval_date.date() == yesterday)
    report_text = (f"🗓️ *Отчет за {yesterday.strftime('%d.%m.%Y')}*\n\n➕ Новых: *{new_yesterday}*\n✅ Одобрено: *{approved_yesterday}*")
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=report_text, parse_mode='MarkdownV2')

async def display_user_card(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    with get_db() as db:
        db_user = get_user(db, user_id)

    if not db_user:
        if update.callback_query:
            await update.callback_query.message.reply_text(f"Пользователь с ID {user_id} не найден в базе данных.")
        else:
            await update.message.reply_text(f"Пользователь с ID {user_id} не найден в базе данных.")
        return

    status = "🚫 Заблокирован" if db_user.is_banned else "⏳ Ожидает" if db_user.awaiting_verification else "✅ Одобрен" if db_user.is_approved else "Новый"
    
    first_seen_str = db_user.first_seen.strftime('%d.%m.%Y %H:%M') if db_user.first_seen else 'Неизвестно'
    last_seen_str = db_user.last_seen.strftime('%d.%m.%Y %H:%M') if db_user.last_seen else 'Неизвестно'
    
    safe_name = escape_markdown(db_user.full_name or 'Неизвестно', version=2)
    safe_user = escape_markdown(db_user.username or 'Нет', version=2)

    card_text = (
        f"👤 *Карточка пользователя*\n\n"
        f"*ID:* `{db_user.user_id}`\n*Имя:* {safe_name}\n*Username:* @{safe_user}\n\n"
        f"*Статус:* {status}\n*Первый визит:* {escape_markdown(first_seen_str, version=2)}\n*Активность:* {escape_markdown(last_seen_str, version=2)}"
    )
    
    action_buttons = []
    if db_user.awaiting_verification: action_buttons.append(InlineKeyboardButton("✅ Одобрить", callback_data=f'user_approve_{user_id}'))
    elif db_user.is_approved: action_buttons.append(InlineKeyboardButton("❌ Отозвать", callback_data=f'user_revoke_{user_id}'))
    
    if user_id != int(ADMIN_CHAT_ID):
        if db_user.is_banned: action_buttons.append(InlineKeyboardButton("✅ Разблок", callback_data=f'user_unblock_{user_id}'))
        else: action_buttons.append(InlineKeyboardButton("🚫 Заблок", callback_data=f'user_block_{user_id}'))

    keyboard = [action_buttons] if action_buttons else []
    keyboard.append([InlineKeyboardButton("💬 Написать", callback_data=f'user_message_{user_id}')])
    keyboard.append([InlineKeyboardButton("⬅️ Новый поиск", callback_data='admin_users'), InlineKeyboardButton("⬅️ В админку", callback_data='admin_main')])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(card_text, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=card_text, parse_mode='MarkdownV2', reply_markup=InlineKeyboardMarkup(keyboard))
