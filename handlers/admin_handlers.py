"""Entry points that glue together admin-related handlers."""

from __future__ import annotations

import asyncio

from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # для старых версий Python

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import get_settings
from db_session import get_db
from keyboards import get_admin_panel_keyboard
from models.crud import (
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
from services.state_manager import StateManager

from .admin.broadcast import (
    broadcast_confirmation_handler,
    prepare_broadcast_message,
    handle_calendar_callback,
    handle_scheduled_broadcast_time_input,
    handle_scheduled_broadcast_confirmation,
    handle_scheduled_broadcasts_list,
    handle_scheduled_broadcast_view,
    handle_broadcast_edit_text_request,
    handle_broadcast_edit_datetime_request,
    handle_broadcast_delete_request,
    handle_broadcast_delete_confirm,
    handle_broadcast_edit_text,
    handle_broadcast_edit_datetime,
    handle_broadcast_edit_media_request,
    handle_broadcast_edit_buttons_request,
    handle_broadcast_confirm_send_request,
    handle_broadcast_edit_media,
    handle_broadcast_edit_buttons,
    handle_broadcast_confirm_now,
    run_broadcast as broadcast_run_broadcast,
)

from .admin.stats import (
    daily_stats_job as stats_daily_stats_job,
    show_stats as stats_show_stats,
    show_status as stats_show_status,
)

settings = get_settings()
logger = settings.logger
from .admin.user_management import (
    approve_user,
    display_user_card,
    handle_direct_message as user_manage_handle_direct_message,
    handle_user_lookup as user_manage_handle_user_lookup,
    reset_user,
)
from .error_handler import handle_errors
from .states import AdminState


async def _handle_user_lookup_wrapper(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    await user_manage_handle_user_lookup(
        update,
        context,
        get_db_fn=get_db,
        get_user_fn=get_user,
        get_user_by_username_fn=get_user_by_username,
        display_user_card_fn=display_user_card,
    )


async def _handle_direct_message_wrapper(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    await user_manage_handle_direct_message(update, context)


@handle_errors
async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.effective_user.id) == settings.ADMIN_CHAT_ID:
        await update.message.reply_text(
            "Добро пожаловать в админ-панель:",
            reply_markup=get_admin_panel_keyboard(),
        )
    else:
        await update.message.reply_text("Извините, эта команда вам недоступна.")


@handle_errors
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state_manager = StateManager(context)
    state = state_manager.get_admin_state()
    handlers = {
        AdminState.BROADCAST_AWAITING_MESSAGE: prepare_broadcast_message,
        AdminState.BROADCAST_SCHEDULE_AWAITING_TIME: handle_scheduled_broadcast_time_input,
        AdminState.BROADCAST_EDIT_AWAITING_TEXT: handle_broadcast_edit_text,
        AdminState.BROADCAST_EDIT_AWAITING_TIME: handle_broadcast_edit_datetime,
        AdminState.BROADCAST_EDIT_AWAITING_MEDIA: handle_broadcast_edit_media,
        AdminState.BROADCAST_EDIT_AWAITING_BUTTONS: handle_broadcast_edit_buttons,
        AdminState.USERS_AWAITING_ID: _handle_user_lookup_wrapper,
        AdminState.USERS_AWAITING_DM: _handle_direct_message_wrapper,
    }
    handler = handlers.get(state)
    if handler:
        await handler(update, context)


@handle_errors
async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None:
        logger.warning("Получен update.callback_query равный None")
        return
        
    await query.answer()
    command = query.data
    logger.info(f"Получена команда в admin_menu_handler: {command}")

    state_manager = StateManager(context)

    # Обработка команд календаря и планирования рассылки
    if command.startswith("calendar_"):
        logger.info(f"Передача команды {command} в handle_calendar_callback")
        await handle_calendar_callback(update, context)
        return

    if command in ["scheduled_broadcast_confirm", "scheduled_broadcast_change_date"]:
        await handle_scheduled_broadcast_confirmation(update, context)
        return

    if command.startswith("scheduled_broadcast_") or command == "scheduled_broadcasts_list":
        if command == "scheduled_broadcasts_list":
            await handle_scheduled_broadcasts_list(update, context)
            return
        elif command.startswith("scheduled_broadcast_view_"):
            await handle_scheduled_broadcast_view(update, context)
            return
        elif command.startswith("scheduled_broadcast_edit_text_"):
            await handle_broadcast_edit_text_request(update, context)
            return
        elif command.startswith("scheduled_broadcast_edit_media_"):
            await handle_broadcast_edit_media_request(update, context)
            return
        elif command.startswith("scheduled_broadcast_edit_buttons_"):
            await handle_broadcast_edit_buttons_request(update, context)
            return
        elif command.startswith("scheduled_broadcast_edit_datetime_"):
            await handle_broadcast_edit_datetime_request(update, context)
            return
        elif command.startswith("scheduled_broadcast_delete_") and not command.endswith("_confirm"):
            await handle_broadcast_delete_request(update, context)
            return
        elif command.startswith("scheduled_broadcast_delete_confirm_"):
            await handle_broadcast_delete_confirm(update, context)
            return
        elif command.startswith("scheduled_broadcast_confirm_send_"):
            await handle_broadcast_confirm_send_request(update, context)
            return
        elif command.startswith("scheduled_broadcast_confirm_now_"):
            await handle_broadcast_confirm_now(update, context)
            return
        elif command.startswith("scheduled_broadcast_cancel_edit"):
            # Отмена редактирования
            state_manager.reset_admin_state()
            await handle_scheduled_broadcasts_list(update, context)
            return

    if command == "admin_main":
        state_manager.reset_admin_state()
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
        # Показываем выбор между новой рассылкой и списком запланированных
        broadcast_keyboard = [
            [InlineKeyboardButton("🆕 Новая рассылка", callback_data="admin_broadcast_new")],
            [InlineKeyboardButton("📋 Все запланированные рассылки", callback_data="admin_broadcast_scheduled_list")]
        ]
        await query.edit_message_text(
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(broadcast_keyboard)
        )
    elif command == "admin_broadcast_new":
        state_manager.reset_admin_state()  # Сбросим любое текущее состояние
        state_manager.set_admin_state(AdminState.BROADCAST_AWAITING_MESSAGE)
        await query.edit_message_text(
            "Режим создания рассылки. Пришлите следующее сообщение, и я подготовлю его к отправке.",
        )
    elif command == "admin_broadcast_scheduled_list":
        await handle_scheduled_broadcasts_list(update, context)
    elif command == "admin_users":
        state_manager.set_admin_state(AdminState.USERS_AWAITING_ID)
        await query.edit_message_text(
            "Режим управления. Отправьте User ID или @username пользователя для поиска.",
        )


@handle_errors
async def show_stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query=None,
    period: str = "all",
) -> None:
    await stats_show_stats(
        update,
        context,
        query=query,
        period=period,
        get_db_fn=get_db,
        count_new_users_fn=count_new_users_on_date,
        count_approved_today_fn=count_approved_users_on_date,
        count_active_today_fn=count_active_users_on_date,
        count_awaiting_fn=count_awaiting_verification_users,
        count_total_fn=count_total_users,
        count_approved_fn=count_approved_users,
        datetime_module=datetime,
    )


@handle_errors
async def show_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query=None,
) -> None:
    await stats_show_status(
        update,
        context,
        query=query,
        get_db_fn=get_db,
        count_total_fn=count_total_users,
        count_active_since_fn=count_active_users_since,
        datetime_module=datetime,
        timedelta_cls=timedelta,
    )


@handle_errors
async def daily_stats_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    await stats_daily_stats_job(
        context,
        get_db_fn=get_db,
        count_new_users_fn=count_new_users_on_date,
        count_approved_users_fn=count_approved_users_on_date,
        datetime_module=datetime,
        timedelta_cls=timedelta,
    )


async def run_broadcast(context: ContextTypes.DEFAULT_TYPE) -> None:
    await broadcast_run_broadcast(
        context,
        iter_targets=iter_broadcast_targets,
        get_db_fn=get_db,
        asyncio_module=asyncio,
    )


__all__ = [
    "show_admin_panel",
    "handle_admin_message",
    "admin_menu_handler",
    "broadcast_confirmation_handler",
    "approve_user",
    "reset_user",
    "show_stats",
    "show_status",
    "daily_stats_job",
    "run_broadcast",
    "display_user_card",
    "get_db",
    "get_user",
    "get_user_by_username",
    "count_active_users_on_date",
    "count_active_users_since",
    "count_approved_users",
    "count_approved_users_on_date",
    "count_awaiting_verification_users",
    "count_new_users_on_date",
    "count_total_users",
    "iter_broadcast_targets",
    "datetime",
    "timedelta",
    "asyncio",
]
