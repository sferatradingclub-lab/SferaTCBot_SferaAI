"""Admin broadcast utilities and handlers."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Optional

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


async def iter_broadcast_targets_optimized(
    db,
    *,
    chunk_size: int = 1000,
    batch_size: int = 100
) -> AsyncGenerator[list[int], None]:
    """
    Оптимизированный итератор ID пользователей для рассылки с пагинацией.
    
    Args:
        db: Сессия базы данных
        chunk_size: Размер чанка для загрузки из базы
        batch_size: Размер батча для отправки сообщений
    """
    admin_id: Optional[int] = None
    if settings.ADMIN_CHAT_ID is not None:
        try:
            admin_id = int(settings.ADMIN_CHAT_ID)
        except (TypeError, ValueError):
            admin_id = None

    query = db.query(User.user_id).filter(User.is_banned.is_(False))
    if admin_id is not None:
        query = query.filter(User.user_id != admin_id)

    current_batch = []
    for row in query.order_by(User.user_id).yield_per(chunk_size):
        user_id = getattr(row, "user_id", row[0])
        current_batch.append(user_id)
        
        if len(current_batch) >= batch_size:
            yield current_batch
            current_batch = []
    
    # Отправляем оставшиеся ID
    if current_batch:
        yield current_batch


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


async def send_broadcast_batch(
    bot,
    user_ids: list[int],
    admin_chat_id: str,
    message_id: int,
    semaphore: asyncio.Semaphore
) -> tuple[int, int, int]:
    """
    Отправляет сообщение батчу пользователей асинхронно.
    
    Args:
        bot: Экземпляр бота
        user_ids: Список ID пользователей для отправки
        admin_chat_id: ID чата администратора
        message_id: ID сообщения для копирования
        semaphore: Семафор для ограничения параллелизма
        
    Returns:
        tuple: (успешно отправлено, заблокировано, ошибки)
    """
    async with semaphore:
        success = 0
        blocked = 0
        error = 0
        
        # Создаем задачи для параллельной отправки
        tasks = []
        for user_id in user_ids:
            task = asyncio.create_task(_send_single_message(bot, user_id, admin_chat_id, message_id))
            tasks.append(task)
        
        # Ждем выполнения всех задач в батче
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты
        for result in results:
            if isinstance(result, Exception):
                # Если была ошибка при отправке
                error += 1
            elif result == "blocked":
                blocked += 1
            elif result == "success":
                success += 1
        
        return success, blocked, error


async def _send_single_message(bot, user_id: int, admin_chat_id: str, message_id: int) -> str:
    """
    Отправляет одно сообщение пользователю с обработкой ошибок.
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        admin_chat_id: ID чата администратора
        message_id: ID сообщения для копирования
        
    Returns:
        str: Статус отправки ("success", "blocked", или исключение)
    """
    try:
        await bot.copy_message(
            chat_id=user_id,
            from_chat_id=admin_chat_id,
            message_id=message_id,
        )
        return "success"
    except TelegramError as err:
        if "bot was blocked" in err.message or "user is deactivated" in err.message:
            return "blocked"
        else:
            # Логируем ошибку, но не возвращаем исключение, чтобы не прерывать весь батч
            logger.warning("Ошибка рассылки пользователю %s: %s", user_id, err)
            return "error"


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
    iter_targets=iter_broadcast_targets_optimized,  # Используем оптимизированную версию
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

    # Ограничиваем количество одновременных запросов к API Telegram
    semaphore = asyncio.Semaphore(20)  # Максимум 20 одновременных отправок

    with get_db_fn() as db:
        # Используем оптимизированный итератор с батчингом
        async for user_batch in iter_targets(db):
            total_targets += len(user_batch)
            # Отправляем батч асинхронно
            batch_success, batch_blocked, batch_error = await send_broadcast_batch(
                context.bot,
                user_batch,
                settings.ADMIN_CHAT_ID,
                message_id_to_send,
                semaphore
            )
            success += batch_success
            blocked += batch_blocked
            error += batch_error

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
