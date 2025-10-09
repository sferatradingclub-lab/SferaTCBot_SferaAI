import asyncio
from datetime import datetime, timedelta
from typing import Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from config import get_settings
from db_session import get_db
from keyboards import get_admin_panel_keyboard
from models.crud import (
    approve_user_in_db,
    ban_user_in_db,
    count_active_users_on_date,
    count_active_users_since,
    count_approved_users,
    count_approved_users_on_date,
    count_awaiting_verification_users,
    count_new_users_on_date,
    count_total_users,
    get_user,
    get_user_by_username,
    iter_broadcast_targets,
)

settings = get_settings()
logger = settings.logger

from .error_handler import handle_errors
from .states import AdminState


def _get_admin_state(context: ContextTypes.DEFAULT_TYPE) -> AdminState:
    raw_state = context.user_data.get("admin_state", AdminState.DEFAULT)
    if isinstance(raw_state, AdminState):
        return raw_state
    legacy_map: Dict[str, AdminState] = {
        "broadcast_awaiting_message": AdminState.BROADCAST_AWAITING_MESSAGE,
        "broadcast_awaiting_confirmation": AdminState.BROADCAST_AWAITING_CONFIRMATION,
        "users_awaiting_id": AdminState.USERS_AWAITING_ID,
        "users_awaiting_dm": AdminState.USERS_AWAITING_DM,
    }
    return legacy_map.get(str(raw_state), AdminState.DEFAULT)


def _set_admin_state(context: ContextTypes.DEFAULT_TYPE, state: AdminState) -> None:
    context.user_data["admin_state"] = state


@handle_errors
async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_user.id) == settings.ADMIN_CHAT_ID:
        await update.message.reply_text(
            "Добро пожаловать в админ-панель:",
            reply_markup=get_admin_panel_keyboard(),
        )
    else:
        await update.message.reply_text("Извините, эта команда вам недоступна.")


async def _handle_broadcast_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.message
    if message is None:
        return

    _set_admin_state(context, AdminState.BROADCAST_AWAITING_CONFIRMATION)
    context.user_data["broadcast_message_id"] = message.message_id
    await context.bot.copy_message(
        chat_id=settings.ADMIN_CHAT_ID,
        from_chat_id=settings.ADMIN_CHAT_ID,
        message_id=message.message_id,
    )
    confirmation_keyboard = [
        [InlineKeyboardButton("✅ Да, отправить всем", callback_data="broadcast_send")],
        [InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel")],
    ]
    await message.reply_text(
        "Вот так будет выглядеть ваше сообщение. Все верно?",
        reply_markup=InlineKeyboardMarkup(confirmation_keyboard),
    )


async def _handle_user_lookup(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.message
    if message is None:
        return

    target_id_str = (message.text or "").strip()
    _set_admin_state(context, AdminState.DEFAULT)

    with get_db() as db:
        if target_id_str.isdigit():
            found_user = get_user(db, int(target_id_str))
        else:
            cleaned_username = target_id_str.replace("@", "").lower()
            found_user = get_user_by_username(db, cleaned_username)

    if found_user:
        await display_user_card(update, context, found_user.user_id)
    else:
        await message.reply_text(f"❌ Пользователь '{target_id_str}' не найден.")


async def _handle_direct_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.message
    if message is None:
        return

    target_user_id = context.user_data.pop("dm_target_user_id", None)
    reply_to_message_id = context.user_data.pop("reply_to_message_id", None)
    _set_admin_state(context, AdminState.DEFAULT)

    if not target_user_id:
        await message.reply_text("❌ Не удалось определить пользователя для ответа.")
        return

    text_to_send = message.text or ""
    try:
        send_kwargs = {
            "chat_id": target_user_id,
            "text": text_to_send,
            "reply_markup": InlineKeyboardMarkup(
                [[InlineKeyboardButton("✍️ Ответить", callback_data="support_from_dm")]]
            ),
        }
        if reply_to_message_id is not None:
            send_kwargs["reply_to_message_id"] = reply_to_message_id

        await context.bot.send_message(**send_kwargs)
        await message.reply_text("✅ Сообщение успешно отправлено!")
    except TelegramError as error:
        logger.error(
            "Не удалось отправить DM пользователю %s: %s",
            target_user_id,
            error.message,
        )
        await message.reply_text(
            f"❌ Не удалось отправить сообщение. Ошибка: {error.message}"
        )


@handle_errors
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _get_admin_state(context)
    handlers = {
        AdminState.BROADCAST_AWAITING_MESSAGE: _handle_broadcast_message,
        AdminState.USERS_AWAITING_ID: _handle_user_lookup,
        AdminState.USERS_AWAITING_DM: _handle_direct_message,
    }
    handler = handlers.get(state)
    if handler:
        await handler(update, context)


@handle_errors
async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    command = query.data

    if command == "admin_main":
        _set_admin_state(context, AdminState.DEFAULT)
        await query.edit_message_text(
            "Добро пожаловать в админ-панель:",
            reply_markup=get_admin_panel_keyboard(),
        )
    elif command == "admin_status":
        await show_status(update, context, query=query)
    elif command == "admin_stats":
        stats_keyboard = [
            [InlineKeyboardButton("За сегодня", callback_data="admin_stats_today")],
            [InlineKeyboardButton("За все время", callback_data="admin_stats_all")],
            [InlineKeyboardButton("⬅️ Назад в админку", callback_data="admin_main")],
        ]
        await query.edit_message_text(
            "Выберите период для просмотра статистики:",
            reply_markup=InlineKeyboardMarkup(stats_keyboard),
        )
    elif command in ["admin_stats_today", "admin_stats_all"]:
        await show_stats(update, context, query=query, period=command.split("_")[-1])
    elif command == "admin_broadcast":
        _set_admin_state(context, AdminState.BROADCAST_AWAITING_MESSAGE)
        await query.edit_message_text(
            "Режим создания рассылки. Пришлите следующее сообщение, и я подготовлю его к отправке.",
        )
    elif command == "admin_users":
        _set_admin_state(context, AdminState.USERS_AWAITING_ID)
        await query.edit_message_text(
            "Режим управления. Отправьте User ID или @username пользователя для поиска.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад в админку", callback_data="admin_main")]]
            ),
        )


@handle_errors
async def broadcast_confirmation_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    await query.answer()
    command = query.data
    _set_admin_state(context, AdminState.DEFAULT)
    if command == "broadcast_send":
        await query.edit_message_text("Начинаю рассылку... Оповещу по завершении.")
        context.job_queue.run_once(run_broadcast, 0)
    elif command == "broadcast_cancel":
        await query.edit_message_text("Рассылка отменена.")
        context.user_data.pop("broadcast_message_id", None)


@handle_errors
async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_user.id) != settings.ADMIN_CHAT_ID:
        return

    try:
        user_id_to_approve = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Ошибка! Используйте: /approve <user_id>")
        return

    with get_db() as db:
        was_updated = approve_user_in_db(db, user_id_to_approve)
        if was_updated:
            logger.info(
                "Админ (%s) одобрил %s",
                update.effective_user.id,
                user_id_to_approve,
            )
            await update.message.reply_text(
                f"✅ Пользователь {user_id_to_approve} успешно одобрен."
            )
            await context.bot.send_message(
                chat_id=user_id_to_approve,
                text="🎉 Поздравляем! Ваша заявка одобрена! Теперь вам доступен полный курс.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🎉 Перейти к полному курсу!", url=settings.FULL_COURSE_URL)]]
                ),
            )
        else:
            await update.message.reply_text(
                f"Ошибка! Пользователь с ID {user_id_to_approve} не найден."
            )


@handle_errors
async def reset_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Функция сброса пользователя требует обновления для работы с БД."
    )


@handle_errors
async def show_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query=None,
    period="all",
) -> None:
    if str(update.effective_user.id) != settings.ADMIN_CHAT_ID:
        return

    today = datetime.now().date()

    with get_db() as db:
        if period == "today":
            new_today = count_new_users_on_date(db, today)
            approved_today = count_approved_users_on_date(db, today)
            active_today = count_active_users_on_date(db, today)
            awaiting = count_awaiting_verification_users(db)
            stats_text = (
                "📊 *Статистика за сегодня*\n\n"
                f"➕ Новых: *{new_today}*\n"
                f"🏃‍♂️ Активных: *{active_today}*\n"
                f"✅ Одобрено: *{approved_today}*\n"
                f"⏳ Ожидает: *{awaiting}*"
            )
        else:
            total = count_total_users(db)
            approved = count_approved_users(db)
            awaiting = count_awaiting_verification_users(db)
            stats_text = (
                "📊 *Статистика за все время*\n\n"
                f"👤 Всего: *{total}*\n"
                f"✅ Одобрено: *{approved}*\n"
                f"⏳ Ожидает: *{awaiting}*"
            )

    if query:
        await query.edit_message_text(
            stats_text,
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⬅️ Назад", callback_data="admin_stats")]]
            ),
        )
    else:
        await update.message.reply_text(stats_text, parse_mode="MarkdownV2")


@handle_errors
async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None) -> None:
    if str(update.effective_user.id) != settings.ADMIN_CHAT_ID:
        return

    now = datetime.now()
    since = now - timedelta(hours=24)

    with get_db() as db:
        total_users = count_total_users(db)
        active_users = count_active_users_since(db, since)

    status_text = (
        "📈 Статус системы\n"
        f"Обновлено: {now.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"🕒 Активны за 24 часа: {active_users}"
    )

    if query:
        await query.message.reply_text(status_text)
    else:
        await update.message.reply_text(status_text)


@handle_errors
async def run_broadcast(context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_user_data = context.application.user_data.get(int(settings.ADMIN_CHAT_ID), {})
    message_id_to_send = admin_user_data.pop("broadcast_message_id", None)
    if not message_id_to_send:
        await context.bot.send_message(
            chat_id=settings.ADMIN_CHAT_ID,
            text="❌ Ошибка: не найдено сообщение для рассылки.",
        )
        return

    success, blocked, error = 0, 0, 0
    total_targets = 0
    logger.info("Начинаю рассылку сообщений.")

    with get_db() as db:
        for user_id in iter_broadcast_targets(db):
            total_targets += 1
            try:
                await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=settings.ADMIN_CHAT_ID,
                    message_id=message_id_to_send,
                )
                success += 1
            except TelegramError as err:
                if "bot was blocked" in err.message or "user is deactivated" in err.message:
                    blocked += 1
                else:
                    error += 1
                    logger.warning("Ошибка рассылки пользователю %s: %s", user_id, err)
            await asyncio.sleep(0.1)

    logger.info("Рассылка завершена. Всего получателей: %s", total_targets)

    report_text = (
        "✅ **Рассылка завершена!**\n\n"
        f"• Успешно: *{success}*\n"
        f"• Заблокировали: *{blocked}*\n"
        f"• Ошибки: *{error}*"
    )
    await context.bot.send_message(
        chat_id=settings.ADMIN_CHAT_ID,
        text=report_text,
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ В админку", callback_data="admin_main")]]
        ),
    )


@handle_errors
async def daily_stats_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    yesterday = (datetime.now() - timedelta(days=1)).date()
    with get_db() as db:
        new_yesterday = count_new_users_on_date(db, yesterday)
        approved_yesterday = count_approved_users_on_date(db, yesterday)
    report_text = (
        "🗓️ *Отчет за {date}*\n\n➕ Новых: *{new}*\n✅ Одобрено: *{approved}*"
    ).format(
        date=yesterday.strftime("%d.%m.%Y"),
        new=new_yesterday,
        approved=approved_yesterday,
    )
    await context.bot.send_message(
        chat_id=settings.ADMIN_CHAT_ID,
        text=report_text,
        parse_mode="MarkdownV2",
    )


@handle_errors
async def display_user_card(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    with get_db() as db:
        db_user = get_user(db, user_id)

    if not db_user:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                f"Пользователь с ID {user_id} не найден в базе данных."
            )
        else:
            await update.message.reply_text(
                f"Пользователь с ID {user_id} не найден в базе данных."
            )
        return

    status = (
        "🚫 Заблокирован"
        if db_user.is_banned
        else "⏳ Ожидает"
        if db_user.awaiting_verification
        else "✅ Одобрен"
        if db_user.is_approved
        else "Новый"
    )

    first_seen_str = (
        db_user.first_seen.strftime("%d.%m.%Y %H:%M") if db_user.first_seen else "Неизвестно"
    )
    last_seen_str = (
        db_user.last_seen.strftime("%d.%m.%Y %H:%M") if db_user.last_seen else "Неизвестно"
    )

    safe_name = escape_markdown(db_user.full_name or "Неизвестно", version=2)
    safe_user = escape_markdown(db_user.username or "Нет", version=2)

    card_text = (
        "👤 *Карточка пользователя*\n\n"
        f"*ID:* `{db_user.user_id}`\n*Имя:* {safe_name}\n*Username:* @{safe_user}\n\n"
        f"*Статус:* {status}\n*Первый визит:* {escape_markdown(first_seen_str, version=2)}\n"
        f"*Активность:* {escape_markdown(last_seen_str, version=2)}"
    )

    action_buttons = []
    if db_user.awaiting_verification:
        action_buttons.append(
            InlineKeyboardButton("✅ Одобрить", callback_data=f"user_approve_{user_id}")
        )
    elif db_user.is_approved:
        action_buttons.append(
            InlineKeyboardButton("❌ Отозвать", callback_data=f"user_revoke_{user_id}")
        )

    if user_id != int(settings.ADMIN_CHAT_ID):
        if db_user.is_banned:
            action_buttons.append(
                InlineKeyboardButton("✅ Разблок", callback_data=f"user_unblock_{user_id}")
            )
        else:
            action_buttons.append(
                InlineKeyboardButton("🚫 Заблок", callback_data=f"user_block_{user_id}")
            )

    keyboard = [action_buttons] if action_buttons else []
    keyboard.append(
        [InlineKeyboardButton("💬 Написать", callback_data=f"user_message_{user_id}")]
    )
    keyboard.append(
        [
            InlineKeyboardButton("⬅️ Новый поиск", callback_data="admin_users"),
            InlineKeyboardButton("⬅️ В админку", callback_data="admin_main"),
        ]
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            card_text,
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=card_text,
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

