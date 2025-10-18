"""Модуль глобального обработчика ошибок для SferaTC Bot."""
import traceback
from pprint import pformat
from telegram import Update
from telegram.ext import ContextTypes
from services.notifier import Notifier
from config import get_settings

settings = get_settings()
logger = settings.logger


def _sanitize_code_block(text: str) -> str:
    """Экранирует тройные кавычки внутри блока кода MarkdownV2."""
    return text.replace("```", "\\`\\`\\`") if text else ""


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок PTB на случай неперехваченных исключений."""
    error = getattr(context, "error", None)

    if isinstance(error, Exception):
        logger.error("Неперехваченное исключение в PTB: %s", error, exc_info=True)
        captured_error = error
    elif error is not None:
        logger.error("Неперехваченное исключение в PTB (неизвестный тип): %r", error)
        captured_error = Exception(str(error))
    else:
        logger.error("Неперехваченное исключение в PTB без объекта ошибки")
        captured_error = Exception("Неизвестная ошибка")

    if isinstance(update, Update):
        try:
            update_repr = pformat(update.to_dict())
        except Exception:  # noqa: BLE001
            update_repr = repr(update)
    else:
        update_repr = repr(update)

    update_block = _sanitize_code_block(update_repr or "None")

    traceback_lines = traceback.format_exception(
        type(captured_error),
        captured_error,
        captured_error.__traceback__,
    )
    traceback_text = "".join(traceback_lines)
    traceback_block = _sanitize_code_block(traceback_text or "Нет данных")

    admin_message = (
        "🔴 *Глобальная ошибка в боте* 🔴\n\n"
        "*Update:*\n"
        f"```\n{update_block}\n```\n\n"
        "*Traceback:*\n"
        f"```traceback\n{traceback_block}\n```"
    )

    bot = getattr(context, "bot", None)
    if not bot:
        return

    notifier = Notifier(bot)
    try:
        await notifier.send_admin_notification(
            admin_message,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
        )
    except Exception as send_error:  # noqa: BLE001
        logger.error(
            "Не удалось отправить сообщение админу о глобальной ошибке: %s",
            send_error,
        )