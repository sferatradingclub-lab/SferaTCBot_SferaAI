"""Централизованный обработчик ошибок для Telegram-бота."""
from __future__ import annotations

import traceback
from functools import wraps
from typing import Any, Awaitable, Callable, Optional

from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from telegram.helpers import escape_markdown

from config import get_settings

settings = get_settings()
logger = settings.logger

UserHandler = Callable[..., Awaitable[Any]]


async def _send_admin_notification(
    func_name: str,
    update: Optional[Update],
    context: Optional[ContextTypes.DEFAULT_TYPE],
    error: Exception,
) -> None:
    """Отправляет детальное уведомление администратору о возникшей ошибке."""
    if not context or not getattr(context, "bot", None):
        return

    user = update.effective_user if update else None
    traceback_lines = traceback.format_exception(type(error), error, error.__traceback__)
    traceback_text = "".join(traceback_lines)

    func_name_safe = escape_markdown(func_name, version=2)

    message_lines = [
        "🔴 *Критическая ошибка в боте* 🔴",
        "",
        f"*Функция:* `{func_name_safe}`",
    ]

    error_text = escape_markdown(str(error), version=2)
    message_lines.append(f"*Ошибка:* {error_text}")

    if user:
        full_name = user.full_name or "Имя не указано"
        username = f"@{user.username}" if user.username else "Нет"
        message_lines.extend(
            [
                "*Пользователь:*",
                f"ID: `{user.id}`",
                f"Имя: {escape_markdown(full_name, version=2)}",
                f"Username: {escape_markdown(username, version=2)}",
            ]
        )
    else:
        message_lines.append("*Пользователь:* Неизвестно")

    message_lines.extend(
        [
            "",
            "*Traceback:*",
            "```traceback",
            traceback_text,
            "```",
        ]
    )

    admin_message = "\n".join(message_lines)

    try:
        await context.bot.send_message(
            chat_id=settings.ADMIN_CHAT_ID,
            text=admin_message,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
        )
    except TelegramError as send_error:
        logger.error(
            "Не удалось отправить уведомление об ошибке админу: %s",
            send_error,
        )


async def _notify_user(update: Optional[Update], context: Optional[ContextTypes.DEFAULT_TYPE]) -> None:
    """Отправляет пользователю безопасное сообщение об ошибке."""
    if not update or not context or not getattr(context, "bot", None):
        return

    chat = update.effective_chat
    if not chat:
        return

    try:
        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "Произошла непредвиденная ошибка. Мы уже работаем над её "
                "устранением. Пожалуйста, попробуйте позже."
            ),
        )
    except TelegramError as user_error:
        logger.warning(
            "Не удалось отправить уведомление пользователю об ошибке: %s",
            user_error,
        )


async def _process_exception(
    func_name: str,
    update: Optional[Update],
    context: Optional[ContextTypes.DEFAULT_TYPE],
    error: Exception,
) -> None:
    """Общая логика обработки исключений для декоратора и глобального хендлера."""
    logger.error(
        "Произошла ошибка в обработчике %s: %s",
        func_name,
        error,
        exc_info=True,
    )
    await _send_admin_notification(func_name, update, context, error)
    await _notify_user(update, context)


def handle_errors(func: UserHandler) -> UserHandler:
    """Декоратор для централизованной обработки ошибок в асинхронных обработчиках."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        update: Optional[Update] = None
        context: Optional[ContextTypes.DEFAULT_TYPE] = None

        for arg in args:
            if update is None and isinstance(arg, Update):
                update = arg
                continue

            if context is None and hasattr(arg, "bot"):
                context = arg

        if kwargs:
            if update is None:
                potential_update = kwargs.get("update")
                if isinstance(potential_update, Update):
                    update = potential_update
            if context is None:
                potential_context = kwargs.get("context")
                if potential_context is not None and hasattr(potential_context, "bot"):
                    context = potential_context

        try:
            return await func(*args, **kwargs)
        except Exception as error:  # noqa: BLE001
            await _process_exception(func.__name__, update, context, error)
            return None

    return wrapper


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок PTB на случай неперехваченных исключений."""
    error = getattr(context, "error", None)
    if isinstance(error, Exception):
        captured_error = error
    elif error is not None:
        captured_error = Exception(str(error))
    else:
        captured_error = Exception("Неизвестная ошибка")
    update_obj = update if isinstance(update, Update) else None
    await _process_exception("global_error_handler", update_obj, context, captured_error)
