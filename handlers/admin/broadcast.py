"""Admin broadcast utilities and handlers."""

from __future__ import annotations

import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from config import get_settings
from models.crud import iter_broadcast_targets
from services.notifier import Notifier
from services.state_manager import StateManager
from handlers.states import AdminState

settings = get_settings()
logger = settings.logger


async def prepare_broadcast_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.message
    if message is None:
        return

    state_manager = StateManager(context)
    state_manager.set_admin_state(AdminState.BROADCAST_AWAITING_CONFIRMATION)
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


async def broadcast_confirmation_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer()
    command = query.data

    state_manager = StateManager(context)
    state_manager.reset_admin_state()

    if command == "broadcast_send":
        await query.edit_message_text("Начинаю рассылку... Оповещу по завершении.")
        context.job_queue.run_once(run_broadcast, 0)
    elif command == "broadcast_cancel":
        await query.edit_message_text("Рассылка отменена.")
        context.user_data.pop("broadcast_message_id", None)


async def run_broadcast(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    iter_targets=iter_broadcast_targets,
    get_db_fn=None,
    asyncio_module=None,
) -> None:
    if get_db_fn is None:
        from handlers import admin_handlers as admin_module

        get_db_fn = admin_module.get_db
    if asyncio_module is None:
        from handlers import admin_handlers as admin_module

        asyncio_module = admin_module.asyncio
    admin_user_data = context.application.user_data.get(int(settings.ADMIN_CHAT_ID), {})
    message_id_to_send = admin_user_data.pop("broadcast_message_id", None)
    notifier = Notifier(context.bot)

    if not message_id_to_send:
        await notifier.send_admin_notification("❌ Ошибка: не найдено сообщение для рассылки.")
        return

    success, blocked, error = 0, 0, 0
    total_targets = 0
    logger.info("Начинаю рассылку сообщений.")

    with get_db_fn() as db:
        for user_id in iter_targets(db):
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
            await asyncio_module.sleep(0.1)

    logger.info("Рассылка завершена. Всего получателей: %s", total_targets)

    title = escape_markdown("Рассылка завершена!", version=2)
    report_text = (
        f"✅ *{title}*\n\n"
        f"• Успешно: *{success}*\n"
        f"• Заблокировали: *{blocked}*\n"
        f"• Ошибки: *{error}*"
    )
    await notifier.send_admin_notification(
        report_text,
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ В админку", callback_data="admin_main")]]
        ),
    )


__all__ = [
    "prepare_broadcast_message",
    "broadcast_confirmation_handler",
    "run_broadcast",
]
