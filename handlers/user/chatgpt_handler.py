"""Handlers that orchestrate ChatGPT conversations with the user."""

from __future__ import annotations

import asyncio
import time
from contextlib import suppress
from typing import Any, Dict, Optional, Set

from telegram import Update
from telegram.error import RetryAfter, TelegramError
from telegram.ext import ContextTypes

from config import get_safe_url, get_safe_video_url, get_settings, send_video_or_photo_fallback, get_video_or_photo_urls
from keyboards import get_chatgpt_keyboard, get_main_menu_keyboard
from services.chatgpt_service import get_chatgpt_response
from services.notifier import Notifier
from services.state_manager import StateManager
from handlers.decorators import user_bootstrap
from handlers.error_handler import handle_errors
from handlers.states import UserState

settings = get_settings()
logger = settings.logger

CHATGPT_SYSTEM_PROMPT = (
    "Ты — универсальный ИИ-ассистент, созданный для помощи пользователю в самых разных задачах. "
    "Твои главные принципы: полезность, точность и безопасность. Всегда стремись дать наиболее "
    "полный и структурированный ответ. Если задача творческая — предлагай оригинальные идеи. "
    "Если техническая — будь точным и приводи примеры. Общайся вежливо и нейтрально. "
    "Категорически избегай генерации вредоносного, неэтичного или оскорбительного контента. "
    "Не давай финансовых или медицинских советов. Твоя цель — быть лучшим инструментом для решения задач пользователя."
)
CHATGPT_CANCELLED_MESSAGE = "Ответ остановлен пользователем."


def _get_chatgpt_task_registry(
    context: ContextTypes.DEFAULT_TYPE,
) -> Optional[Dict[int, Set[asyncio.Task[Any]]]]:
    application = getattr(context, "application", None)
    if application is None:
        return None

    registry = getattr(application, "_chatgpt_streaming_tasks", None)
    if registry is None:
        registry = {}
        setattr(application, "_chatgpt_streaming_tasks", registry)

    return registry


def _register_chatgpt_streaming_task(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: Optional[int],
    task: asyncio.Task[Any],
) -> None:
    if user_id is None:
        return

    registry = _get_chatgpt_task_registry(context)
    if registry is None:
        return

    active_tasks = registry.setdefault(user_id, set())

    def _cleanup(done_task: asyncio.Task[Any]) -> None:
        active_tasks.discard(done_task)
        if not active_tasks:
            registry.pop(user_id, None)

    active_tasks.add(task)
    task.add_done_callback(lambda finished: _cleanup(finished))


async def cancel_active_chatgpt_tasks(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: Optional[int],
    *,
    exclude: Optional[asyncio.Task[Any]] = None,
) -> bool:
    if user_id is None:
        return False

    registry = _get_chatgpt_task_registry(context)
    if not registry:
        return False

    active_tasks = registry.get(user_id)
    if not active_tasks:
        return False

    to_cancel: list[asyncio.Task[Any]] = []

    for task in list(active_tasks):
        if task is exclude:
            continue
        if task.done():
            active_tasks.discard(task)
            continue
        task.cancel()
        to_cancel.append(task)

    if to_cancel:
        await asyncio.gather(*to_cancel, return_exceptions=True)

    if not active_tasks:
        registry.pop(user_id, None)
        if not registry:
            application = getattr(context, "application", None)
            if application and hasattr(application, "_chatgpt_streaming_tasks"):
                delattr(application, "_chatgpt_streaming_tasks")

    return bool(to_cancel)


@handle_errors
@user_bootstrap
async def show_chatgpt_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user,
    is_new_user: bool,
) -> None:
    state_manager = StateManager(context)
    state_manager.set_user_state(UserState.CHATGPT_ACTIVE)
    context.user_data["chat_history"] = [
        {"role": "system", "content": CHATGPT_SYSTEM_PROMPT}
    ]

    if update.message is None:
        return

    chatgpt_caption = (
        "Вы начали диалог с ИИ-ассистентом. Просто отправьте ваше сообщение. "
        "Чтобы закончить, нажмите кнопку ниже или введите /stop_chat."
    )
    # Используем отдельные переменные для видео и изображения
    chatgpt_video_url, chatgpt_photo_url = get_video_or_photo_urls(settings, "CHATGPT")
    
    await send_video_or_photo_fallback(
        message=update.message,
        video_url=chatgpt_video_url,
        photo_url=chatgpt_photo_url,
        caption=chatgpt_caption,
        reply_markup=get_chatgpt_keyboard()
    )


@handle_errors
@user_bootstrap
async def stop_chatgpt_session(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user,
    is_new_user: bool,
) -> None:
    await perform_chatgpt_stop(update, context)


async def handle_streaming_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message and message.text == "Закончить диалог":
        await perform_chatgpt_stop(update, context)
        return

    wait_text = "Пожалуйста, подождите, пока я закончу отвечать на предыдущий запрос."
    if message and hasattr(message, "reply_text"):
        await message.reply_text(wait_text)
    elif update.effective_chat:
        notifier = Notifier(context.bot)
        await notifier.send_message(chat_id=update.effective_chat.id, text=wait_text)


async def perform_chatgpt_stop(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    context.user_data["_chatgpt_cancelled_by_user"] = True

    current_task = asyncio.current_task()
    user = getattr(update, "effective_user", None)
    user_id = getattr(user, "id", None)
    await cancel_active_chatgpt_tasks(context, user_id, exclude=current_task)

    state_manager = StateManager(context)
    state_manager.reset_user_state()
    context.user_data.pop("chat_history", None)

    if update.message is None:
        return

    keyboard = get_main_menu_keyboard(user.id) if user else None

    await update.message.reply_text(
        "Диалог завершен. Вы вернулись в главное меню.",
        reply_markup=keyboard,
    )


async def handle_chatgpt_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        if update.effective_chat:
            notifier = Notifier(context.bot)
            await notifier.send_message(
                chat_id=update.effective_chat.id,
                text="Пожалуйста, отправьте текстовое сообщение.",
                reply_markup=get_chatgpt_keyboard(),
            )
        return

    if message.text == "Закончить диалог":
        await perform_chatgpt_stop(update, context)
        return

    if context.application is None:
        await message.reply_text("Мне не удалось обратиться к ChatGPT. Попробуйте позже.")
        return

    state_manager = StateManager(context)
    state_manager.set_user_state(UserState.CHATGPT_STREAMING)
    context.user_data.pop("_chatgpt_cancelled_by_user", None)

    streaming_sessions = context.user_data.get("_chatgpt_streaming_sessions", 0) + 1
    context.user_data["_chatgpt_streaming_sessions"] = streaming_sessions

    user = getattr(update, "effective_user", None)
    task = context.application.create_task(
        stream_chatgpt_response(update, context),
        name=f"chatgpt-stream-{getattr(message, 'message_id', 'unknown')}",
    )

    _register_chatgpt_streaming_task(context, getattr(user, "id", None), task)


async def stream_chatgpt_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.message
    if message is None or not message.text:
        return

    user_text = message.text
    placeholder_message = None
    bot = getattr(context, "bot", None)
    chat_id = update.effective_chat.id if update.effective_chat else None
    message_id: Optional[int] = None

    try:
        placeholder_message = await message.reply_text("✍️")
    except TelegramError as error:
        logger.warning("Не удалось отправить placeholder для ChatGPT: %s", error)
    except asyncio.CancelledError:
        context.user_data["_chatgpt_cancelled_by_user"] = True
        raise

    if placeholder_message is not None:
        chat_id = getattr(placeholder_message, "chat_id", chat_id)
        message_id = getattr(placeholder_message, "message_id", None)

    async def _edit_placeholder(text: str, *, show_typing: bool = False) -> None:
        nonlocal placeholder_message, message_id, chat_id
        display_text = text
        if show_typing:
            display_text = f"{text} ✍️" if text else "✍️"

        target_bot = bot or getattr(context, "bot", None)
        if target_bot and chat_id is not None and message_id is not None:
            await target_bot.edit_message_text(
                text=display_text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=None,
            )
        elif placeholder_message is not None and hasattr(placeholder_message, "edit_text"):
            await placeholder_message.edit_text(text=display_text, reply_markup=None)
        else:
            new_message = await message.reply_text(display_text, reply_markup=None)
            placeholder_message = new_message
            chat_id = getattr(new_message, "chat_id", chat_id)
            message_id = getattr(new_message, "message_id", None)

    async def _send_new_placeholder() -> None:
        nonlocal placeholder_message, message_id, chat_id

        target_chat_id = chat_id or (update.effective_chat.id if update.effective_chat else None)
        if target_chat_id is None:
            placeholder_message = None
            message_id = None
            return

        target_bot = bot or getattr(context, "bot", None)
        try:
            if target_bot is not None:
                placeholder_message = await target_bot.send_message(chat_id=target_chat_id, text="✍️")
            else:
                placeholder_message = await message.reply_text("✍️")
        except TelegramError as error:
            logger.warning(
                "Не удалось отправить дополнительное placeholder-сообщение для ChatGPT: %s",
                error,
            )
            placeholder_message = None
            message_id = None
            return

        chat_id = getattr(placeholder_message, "chat_id", chat_id)
        message_id = getattr(placeholder_message, "message_id", None)

    full_response_parts: list[str] = []
    current_message_text = ""
    buffer = ""
    final_response_text = ""

    def _get_full_response_text() -> str:
        return "".join(full_response_parts) + current_message_text

    history = context.user_data.get("chat_history") or [
        {"role": "system", "content": CHATGPT_SYSTEM_PROMPT}
    ]
    history = list(history)
    history.append({"role": "user", "content": user_text})

    if len(history) > 11:
        system_message = history[0] if history and history[0].get("role") == "system" else None
        recent_messages = history[-10:]
        history = ([system_message] + recent_messages) if system_message else recent_messages

    context.user_data["chat_history"] = history

    def _count_words(text: str) -> int:
        stripped = text.strip()
        if not stripped:
            return 0
        return len([word for word in stripped.split() if word])

    last_edit_time = time.time()
    stream_failed = False
    failure_message = "Мне не удалось сгенерировать ответ. Попробуйте позже."
    telegram_max_message_length = 4096
    streaming_max_message_length = telegram_max_message_length - 2

    response_stream: Optional[Any] = None
    cancelled_by_user = False

    buffer_word_count = 0

    try:
        response_stream = get_chatgpt_response(history, context.application)
        active_streams = context.user_data.setdefault("_chatgpt_active_streams", set())
        active_streams.add(response_stream)

        state_manager = StateManager(context)

        async for chunk in response_stream:
            if state_manager.get_user_state() != UserState.CHATGPT_STREAMING:
                logger.info("Стриминг был прерван досрочно.")
                cancelled_by_user = bool(context.user_data.get("_chatgpt_cancelled_by_user"))
                if buffer:
                    buffer = ""
                current_message_text = ""
                with suppress(TelegramError):
                    await _edit_placeholder(CHATGPT_CANCELLED_MESSAGE, show_typing=False)
                if response_stream is not None:
                    with suppress(Exception):
                        await response_stream.aclose()
                break

            if not chunk:
                continue

            buffer += chunk
            buffer_word_count = _count_words(buffer)

            while buffer:
                available_space = telegram_max_message_length - len(current_message_text)
                if available_space <= 0:
                    if current_message_text:
                        with suppress(TelegramError):
                            await _edit_placeholder(current_message_text, show_typing=False)
                        full_response_parts.append(current_message_text)
                        current_message_text = ""
                    await _send_new_placeholder()
                    last_edit_time = time.time() - settings.STREAM_EDIT_INTERVAL_SECONDS
                    continue

                if (
                    len(current_message_text) + len(buffer) > streaming_max_message_length
                    or len(buffer) > available_space
                ):
                    portion = buffer[:available_space]
                    logger.warning(
                        "Сообщение достигло максимальной длины. Продолжаю стрим в новом сообщении."
                    )
                    try:
                        await _edit_placeholder(current_message_text + portion, show_typing=False)
                    except TelegramError as error:
                        if "Message is not modified" not in str(error):
                            logger.warning(
                                "Не удалось зафиксировать переполненное сообщение ChatGPT: %s",
                                error,
                            )
                    current_message_text += portion
                    buffer = buffer[len(portion):]
                    buffer_word_count = _count_words(buffer)
                    if current_message_text:
                        full_response_parts.append(current_message_text)
                        current_message_text = ""
                    await _send_new_placeholder()
                    last_edit_time = time.time() - settings.STREAM_EDIT_INTERVAL_SECONDS
                    continue

                break

            current_time = time.time()
            has_time_budget = (
                current_time - last_edit_time
            ) >= settings.STREAM_EDIT_INTERVAL_SECONDS
            reached_word_threshold = (
                buffer_word_count >= settings.STREAM_BUFFER_SIZE_WORDS
            )
            near_length_limit = (
                len(current_message_text) + len(buffer)
            ) > streaming_max_message_length

            should_update = bool(buffer) and (
                near_length_limit or reached_word_threshold or has_time_budget
            )

            if should_update:
                try:
                    await _edit_placeholder(current_message_text + buffer, show_typing=True)
                    current_message_text += buffer
                    buffer = ""
                    buffer_word_count = 0
                    last_edit_time = time.time()
                except TelegramError as error:
                    error_message = str(error)
                    if "Message is not modified" in error_message:
                        continue

                    if isinstance(error, RetryAfter):
                        retry_delay = max(
                            float(getattr(error, "retry_after", 0)),
                            settings.STREAM_EDIT_INTERVAL_SECONDS,
                        )
                        logger.warning(
                            "Получен сигнал flood control (RetryAfter=%s). Пауза перед повтором.",
                            getattr(error, "retry_after", None),
                        )
                        await asyncio.sleep(retry_delay)
                        last_edit_time = time.time()
                    else:
                        logger.warning(
                            "Не удалось обновить потоковое сообщение ChatGPT: %s", error
                        )
                        last_edit_time = time.time()
        else:
            if buffer:
                try:
                    await _edit_placeholder(current_message_text + buffer, show_typing=False)
                    current_message_text += buffer
                    buffer = ""
                    buffer_word_count = 0
                except TelegramError as error:
                    if "Message is not modified" not in str(error):
                        logger.warning("Не удалось завершить потоковое сообщение ChatGPT: %s", error)
            else:
                if current_message_text:
                    with suppress(TelegramError):
                        await _edit_placeholder(current_message_text, show_typing=False)

    except asyncio.CancelledError:
        cancelled_by_user = True
        if response_stream is not None:
            with suppress(Exception):
                await response_stream.aclose()
        if buffer:
            buffer = ""
        current_message_text = ""
        with suppress(TelegramError):
            await _edit_placeholder(CHATGPT_CANCELLED_MESSAGE, show_typing=False)
        context.user_data["_chatgpt_cancelled_by_user"] = True
    except Exception as error:  # pragma: no cover - логирование ошибки
        stream_failed = True
        logger.error("Ошибка при получении ответа от ChatGPT: %s", error, exc_info=True)
        state_manager = StateManager(context)
        if state_manager.get_user_state() == UserState.CHATGPT_STREAMING:
            await _edit_placeholder(failure_message, show_typing=False)
    finally:
        final_response_text = _get_full_response_text()
        cancelled_by_user = cancelled_by_user or bool(context.user_data.get("_chatgpt_cancelled_by_user"))
        streaming_sessions = context.user_data.get("_chatgpt_streaming_sessions", 0) - 1
        if streaming_sessions > 0:
            context.user_data["_chatgpt_streaming_sessions"] = streaming_sessions
        else:
            context.user_data.pop("_chatgpt_streaming_sessions", None)
            state_manager = StateManager(context)
            if state_manager.get_user_state() == UserState.CHATGPT_STREAMING:
                state_manager.set_user_state(UserState.CHATGPT_ACTIVE)
            if cancelled_by_user:
                context.user_data.pop("_chatgpt_cancelled_by_user", None)

    if (
        not stream_failed
        and not cancelled_by_user
        and final_response_text
        and final_response_text.strip()
        and "chat_history" in context.user_data
    ):
        context.user_data["chat_history"].append({"role": "assistant", "content": final_response_text})


__all__ = [
    "CHATGPT_SYSTEM_PROMPT",
    "show_chatgpt_menu",
    "stop_chatgpt_session",
    "handle_chatgpt_message",
    "handle_streaming_state",
    "cancel_active_chatgpt_tasks",
    "stream_chatgpt_response",
    "perform_chatgpt_stop",
]
