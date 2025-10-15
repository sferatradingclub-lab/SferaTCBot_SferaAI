import asyncio
import time

from typing import Any, Awaitable, Callable, Dict, Optional, Set

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from config import get_safe_url, get_settings
from keyboards import (
    get_channel_keyboard,
    get_chatgpt_keyboard,
    get_main_menu_keyboard,
    get_psychologist_keyboard,
    get_support_llm_keyboard,
    get_training_keyboard,
)
from models.user import User
from services.chatgpt_service import get_chatgpt_response

from .admin_handlers import handle_admin_message
from .decorators import user_bootstrap
from .error_handler import handle_errors
from .states import AdminState, UserState
from .verification_handlers import (
    handle_id_submission,
    handle_support_message,
    start_verification_process,
)

settings = get_settings()
logger = settings.logger

SupportPromptSender = Callable[[str], Awaitable[object]]
SUPPORT_ESCALATION_PROMPT = "Опишите вашу проблему одним сообщением, и мы передадим его администратору."
FRIENDLY_MAIN_MENU_REMINDER = "Выберите действие в меню ниже:"
CHATGPT_SYSTEM_PROMPT = (
    "Ты — универсальный ИИ-ассистент, созданный для помощи пользователю в самых разных задачах. "
    "Твои главные принципы: полезность, точность и безопасность. Всегда стремись дать наиболее "
    "полный и структурированный ответ. Если задача творческая — предлагай оригинальные идеи. "
    "Если техническая — будь точным и приводи примеры. Общайся вежливо и нейтрально. "
    "Категорически избегай генерации вредоносного, неэтичного или оскорбительного контента. "
    "Не давай финансовых или медицинских советов. Твоя цель — быть лучшим инструментом для решения задач пользователя."
)
CHATGPT_CANCELLED_MESSAGE = "Ответ остановлен пользователем."


def _get_user_state(context: ContextTypes.DEFAULT_TYPE) -> UserState:
    raw_state = context.user_data.get("state", UserState.DEFAULT)
    if isinstance(raw_state, UserState):
        return raw_state
    legacy_map: Dict[str, UserState] = {
        "chatgpt_active": UserState.CHATGPT_ACTIVE,
        "support_llm_active": UserState.SUPPORT_LLM_ACTIVE,
        "awaiting_support_message": UserState.AWAITING_SUPPORT_MESSAGE,
    }
    return legacy_map.get(str(raw_state), UserState.DEFAULT)


def _set_user_state(context: ContextTypes.DEFAULT_TYPE, state: UserState) -> None:
    context.user_data["state"] = state


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


def _ensure_manual_support_state(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Готовит состояние для ручной поддержки."""

    already_manual = _get_user_state(context) == UserState.AWAITING_SUPPORT_MESSAGE
    _set_user_state(context, UserState.AWAITING_SUPPORT_MESSAGE)

    return not already_manual


async def _activate_manual_support(
    context: ContextTypes.DEFAULT_TYPE,
    prompt_sender: SupportPromptSender,
) -> None:
    """Переводит пользователя в ручной режим и отправляет подсказку, если нужно."""

    first_manual_transition = _ensure_manual_support_state(context)

    if first_manual_transition:
        context.user_data.pop("support_llm_history", None)
        context.user_data["support_thank_you_sent"] = False

        try:
            await prompt_sender(SUPPORT_ESCALATION_PROMPT)
        except Exception as error:  # pragma: no cover - логирование ошибки
            logger.error(
                "Не удалось отправить подсказку для ручной поддержки: %s",
                error,
            )


def _set_default_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    _set_user_state(context, UserState.DEFAULT)


@handle_errors
@user_bootstrap
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user: Optional[User],
    is_new_user: bool,
) -> None:
    user = update.effective_user

    if is_new_user and user is not None:
        logger.info(f"Новый пользователь: {user.id} ({user.full_name}) @{user.username}")
        user_fullname = escape_markdown(user.full_name or "Имя не указано", version=2)
        user_username = (
            f"@{escape_markdown(user.username, version=2)}" if user.username else "Нет"
        )
        admin_message = (
            "👋 Новый пользователь\!\n\n"
            f"Имя: {user_fullname}\nUsername: {user_username}\nID: `{user.id}`"
        )
        try:
            await context.bot.send_message(
                chat_id=settings.ADMIN_CHAT_ID,
                text=admin_message,
                parse_mode="MarkdownV2",
            )
        except Exception as error:  # pragma: no cover - логирование ошибки
            logger.error(
                "Не удалось отправить уведомление о новом пользователе админу: %s",
                error,
            )
            raise

    payload = " ".join(context.args)
    if payload == "trial_completed":
        _set_user_state(context, UserState.AWAITING_VERIFICATION_ID)
        await start_verification_process(update, context)
        return

    if user is None or update.message is None:
        return

    welcome_caption = (
        f"Привет, {user.first_name}!\n\n"
        "Добро пожаловать в экосистему SferaTC. Здесь ты найдешь все для успешного старта в трейдинге.\n\n"
        "Чтобы быть в курсе всех обновлений, подпишись на наш основной канал!"
    )
    welcome_photo_url = get_safe_url(settings.WELCOME_IMAGE_URL, "welcome_image")
    if welcome_photo_url:
        await update.message.reply_photo(
            photo=welcome_photo_url,
            caption=welcome_caption,
            reply_markup=get_channel_keyboard(),
        )
    else:
        await update.message.reply_text(
            welcome_caption,
            reply_markup=get_channel_keyboard(),
        )
    await update.message.reply_text(
        "Выберите действие в меню ниже:",
        reply_markup=get_main_menu_keyboard(user.id),
    )


@handle_errors
@user_bootstrap
async def show_training_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user: Optional[User],
    is_new_user: bool,
) -> None:
    is_approved = bool(db_user.is_approved) if db_user else False

    if update.message is None:
        return

    caption = "Наше бесплатное обучение проходит в специальном чат-боте на платформе ChatGPT."
    text = "Ты уже получил доступ к полному курсу!"

    if is_approved:
        await update.message.reply_text(
            text,
            reply_markup=get_training_keyboard(is_approved),
        )
    else:
        training_photo_url = get_safe_url(settings.TRAINING_IMAGE_URL, "training_image")
        if training_photo_url:
            await update.message.reply_photo(
                photo=training_photo_url,
                caption=caption,
                reply_markup=get_training_keyboard(is_approved),
            )
        else:
            await update.message.reply_text(
                caption,
                reply_markup=get_training_keyboard(is_approved),
            )


@handle_errors
@user_bootstrap
async def show_psychologist_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user: Optional[User],
    is_new_user: bool,
) -> None:
    if update.message is None:
        return

    psychologist_photo_url = get_safe_url(settings.PSYCHOLOGIST_IMAGE_URL, "psychologist_image")
    caption = "Наш ИИ-психолог поможет справиться со стрессом в трейдинге."
    if psychologist_photo_url:
        await update.message.reply_photo(
            photo=psychologist_photo_url,
            caption=caption,
            reply_markup=get_psychologist_keyboard(),
        )
    else:
        await update.message.reply_text(
            caption,
            reply_markup=get_psychologist_keyboard(),
        )


@handle_errors
@user_bootstrap
async def show_chatgpt_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user: Optional[User],
    is_new_user: bool,
) -> None:
    _set_user_state(context, UserState.CHATGPT_ACTIVE)
    context.user_data["chat_history"] = [
        {"role": "system", "content": CHATGPT_SYSTEM_PROMPT}
    ]

    if update.message is None:
        return

    await update.message.reply_text(
        "Вы начали диалог с ИИ-ассистентом. Просто отправьте ваше сообщение. "
        "Чтобы закончить, нажмите кнопку ниже или введите /stop_chat.",
        reply_markup=get_chatgpt_keyboard(),
    )


@handle_errors
@user_bootstrap
async def stop_chatgpt_session(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user: Optional[User],
    is_new_user: bool,
) -> None:
    await _perform_chatgpt_stop(update, context)


@handle_errors
@user_bootstrap
async def show_support_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user: Optional[User],
    is_new_user: bool,
) -> None:
    _set_user_state(context, UserState.SUPPORT_LLM_ACTIVE)
    context.user_data["support_llm_history"] = [
        {"role": "system", "content": settings.SUPPORT_LLM_SYSTEM_PROMPT}
    ]

    if update.message is None:
        return

    support_caption = (
        "Я — ИИ-поддержка SferaTC и готов помочь. Опишите проблему текстом, а если понадобится человек, "
        f"нажмите кнопку «{settings.SUPPORT_ESCALATION_BUTTON_TEXT}»."
    )
    support_photo_url = get_safe_url(settings.SUPPORT_IMAGE_URL, "support_image")
    if support_photo_url:
        await update.message.reply_photo(
            photo=support_photo_url,
            caption=support_caption,
            reply_markup=get_support_llm_keyboard(),
        )
    else:
        await update.message.reply_text(
            support_caption,
            reply_markup=get_support_llm_keyboard(),
        )


@handle_errors
@user_bootstrap
async def escalate_support_to_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user: Optional[User],
    is_new_user: bool,
) -> None:
    query = update.callback_query
    if query is None:
        return

    await query.answer("Подключаю администратора…")
    message = query.message
    if message:
        try:
            if message.text:
                await message.edit_reply_markup(reply_markup=None)
            elif message.caption:
                await message.edit_caption(caption=message.caption, reply_markup=None)
        except TelegramError as error:
            logger.warning(f"Не удалось обновить сообщение поддержки: {error}")
        await _activate_manual_support(context, message.reply_text)


@handle_errors
@user_bootstrap
async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user: Optional[User],
    is_new_user: bool,
) -> None:
    if update.message is None:
        return

    await update.message.reply_text(
        "Это бот образовательной экосистемы SferaTC. Используйте меню для навигации по разделам."
    )


async def _handle_chatgpt_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Пожалуйста, отправьте текстовое сообщение.",
                reply_markup=get_chatgpt_keyboard(),
            )
        return

    if message.text == "Закончить диалог":
        await stop_chatgpt_session(update, context)
        return

    placeholder_message = await message.reply_text("✍️")
    streaming_sessions = context.user_data.get("_chatgpt_streaming_sessions", 0) + 1
    context.user_data["_chatgpt_streaming_sessions"] = streaming_sessions
    _set_user_state(context, UserState.CHATGPT_STREAMING)
    current_task = asyncio.current_task()
    if current_task is not None:
        active_tasks: Set[Any] = context.user_data.setdefault("_chatgpt_streaming_tasks", set())
        active_tasks.add(current_task)
    chat_id = getattr(placeholder_message, "chat_id", update.effective_chat.id if update.effective_chat else None)
    message_id = getattr(placeholder_message, "message_id", None)
    bot = getattr(context, "bot", None)

    async def _edit_placeholder(text: str) -> None:
        if bot and chat_id is not None and message_id is not None:
            # Отправляем только текст, клавиатура управляется отдельно
            await context.bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=None,
            )
        elif hasattr(placeholder_message, "edit_text"):
            await placeholder_message.edit_text(text=text, reply_markup=None)
        else:
            await message.reply_text(text, reply_markup=None)

    history = context.user_data.get("chat_history") or [
        {"role": "system", "content": CHATGPT_SYSTEM_PROMPT}
    ]
    history = list(history)
    history.append({"role": "user", "content": message.text})

    if len(history) > 11:
        system_message = history[0] if history and history[0].get("role") == "system" else None
        recent_messages = history[-10:]
        history = ([system_message] + recent_messages) if system_message else recent_messages

    context.user_data["chat_history"] = history

    full_response_text = ""
    buffer = ""
    last_edit_time = time.time()
    stream_failed = False
    failure_message = "Мне не удалось сгенерировать ответ. Попробуйте позже."
    TELEGRAM_MAX_MESSAGE_LENGTH = 4096

    response_stream: Optional[Any] = None
    cancelled_by_user = False

    try:
        response_stream = get_chatgpt_response(history, context.application)
        active_streams = context.user_data.setdefault("_chatgpt_active_streams", set())
        active_streams.add(response_stream)

        async for chunk in response_stream:
            if _get_user_state(context) != UserState.CHATGPT_STREAMING:
                logger.info("Стриминг был прерван досрочно.")
                cancelled_by_user = bool(context.user_data.get("_chatgpt_cancelled_by_user"))
                if full_response_text:
                    await _edit_placeholder(full_response_text)
                else:
                    await _edit_placeholder(CHATGPT_CANCELLED_MESSAGE)
                try:
                    await response_stream.aclose()
                except RuntimeError:
                    # Поток ещё исполняется – закроется в блоке finally.
                    pass
                except Exception as close_error:  # pragma: no cover - логирование для диагностики
                    logger.warning(
                        "Не удалось завершить поток ChatGPT при остановке пользователем: %s",
                        close_error,
                    )
                break

            if not chunk:
                continue

            buffer += chunk

            # Проактивная проверка на переполнение
            if len(full_response_text + buffer) + 2 >= TELEGRAM_MAX_MESSAGE_LENGTH:
                logger.warning("Сообщение достигло максимальной длины. Отправляю остаток в новом сообщении.")
                await _edit_placeholder(full_response_text)

                remaining_text = buffer
                async for remaining_chunk in response_stream:
                    remaining_text += remaining_chunk

                full_response_text += remaining_text

                for i in range(0, len(remaining_text), TELEGRAM_MAX_MESSAGE_LENGTH):
                    await message.reply_text(text=remaining_text[i:i + TELEGRAM_MAX_MESSAGE_LENGTH])
                buffer = "" # Буфер полностью обработан
                break

            current_time = time.time()
            should_update = bool(buffer) and (
                (current_time - last_edit_time) > settings.STREAM_EDIT_INTERVAL_SECONDS
                or len(buffer.split()) > settings.STREAM_BUFFER_SIZE_WORDS
            )

            if should_update:
                try:
                    await _edit_placeholder(f"{full_response_text}{buffer} ✍️")
                    full_response_text += buffer
                    buffer = ""
                    last_edit_time = current_time
                except TelegramError as e:
                    if "Message is not modified" not in str(e):
                        logger.warning("Не удалось обновить потоковое сообщение ChatGPT: %s", e)
        else:
            final_text = full_response_text + buffer
            if final_text:
                if len(final_text) > TELEGRAM_MAX_MESSAGE_LENGTH:
                    safe_text = final_text[:TELEGRAM_MAX_MESSAGE_LENGTH]
                    await _edit_placeholder(safe_text)

                    remaining_text = final_text[TELEGRAM_MAX_MESSAGE_LENGTH:]
                    for i in range(0, len(remaining_text), TELEGRAM_MAX_MESSAGE_LENGTH):
                        await message.reply_text(
                            text=remaining_text[i : i + TELEGRAM_MAX_MESSAGE_LENGTH]
                        )
                else:
                    await _edit_placeholder(final_text)
                full_response_text = final_text

    except Exception as error:
        stream_failed = True
        logger.error("Ошибка при получении ответа от ChatGPT: %s", error, exc_info=True)
        if _get_user_state(context) == UserState.CHATGPT_STREAMING:
            await _edit_placeholder(failure_message)
    finally:
        cancelled_by_user = cancelled_by_user or bool(context.user_data.get("_chatgpt_cancelled_by_user"))
        active_streams = context.user_data.get("_chatgpt_active_streams")
        if active_streams and response_stream is not None:
            active_streams.discard(response_stream)
            if not active_streams:
                context.user_data.pop("_chatgpt_active_streams", None)
        if current_task is not None:
            active_tasks = context.user_data.get("_chatgpt_streaming_tasks")
            if active_tasks:
                active_tasks.discard(current_task)
                if not active_tasks:
                    context.user_data.pop("_chatgpt_streaming_tasks", None)
        streaming_sessions = context.user_data.get("_chatgpt_streaming_sessions", 0) - 1
        if streaming_sessions > 0:
            context.user_data["_chatgpt_streaming_sessions"] = streaming_sessions
        else:
            context.user_data.pop("_chatgpt_streaming_sessions", None)
            if _get_user_state(context) == UserState.CHATGPT_STREAMING:
                _set_user_state(context, UserState.CHATGPT_ACTIVE)
            if cancelled_by_user:
                context.user_data.pop("_chatgpt_cancelled_by_user", None)

    if (
        not stream_failed
        and not cancelled_by_user
        and full_response_text
        and full_response_text.strip()
        and "chat_history" in context.user_data
    ):
        context.user_data["chat_history"].append({"role": "assistant", "content": full_response_text})


async def _handle_support_llm_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.message
    text = (message.text or "").strip() if message else ""

    if text.lower() == settings.SUPPORT_ESCALATION_BUTTON_TEXT.lower():
        await _activate_manual_support(context, message.reply_text)
        return

    if not text:
        if message:
            await message.reply_text(
                "ИИ-поддержка сейчас работает только с текстовыми сообщениями. "
                f"Опишите вопрос словами или нажмите «{settings.SUPPORT_ESCALATION_BUTTON_TEXT}».",
                reply_markup=get_support_llm_keyboard(),
            )
        return

    history = context.user_data.get("support_llm_history") or [
        {"role": "system", "content": settings.SUPPORT_LLM_SYSTEM_PROMPT}
    ]
    history = history + [{"role": "user", "content": text}]

    if len(history) > settings.SUPPORT_LLM_HISTORY_LIMIT + 1:
        history = [history[0]] + history[-settings.SUPPORT_LLM_HISTORY_LIMIT:]

    context.user_data["support_llm_history"] = history
    
    response_chunks = [
        chunk async for chunk in get_chatgpt_response(history, context.application)
    ]
    response_text = "".join(response_chunks)

    if response_text and response_text.strip():
        history.append({"role": "assistant", "content": response_text})
        context.user_data["support_llm_history"] = history
        if message:
            await message.reply_text(
                response_text,
                reply_markup=get_support_llm_keyboard(),
            )
    else:
        if message:
            await message.reply_text(
                "Мне не удалось решить вопрос. Попробуйте переформулировать или нажмите «"
                f"{settings.SUPPORT_ESCALATION_BUTTON_TEXT}».",
                reply_markup=get_support_llm_keyboard(),
            )


async def _handle_manual_support_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.message
    if message is None:
        return

    if message.text == "Вернуться в меню":
        _set_default_state(context)
        await message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=get_main_menu_keyboard(update.effective_user.id),
        )
        return

    await handle_support_message(update, context)


async def _send_main_menu_reminder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: Optional[int],
) -> None:
    reminder_text = FRIENDLY_MAIN_MENU_REMINDER
    menu_keyboard = get_main_menu_keyboard(user_id) if user_id else None
    message = update.message

    if message and hasattr(message, "reply_text"):
        await message.reply_text(reminder_text, reply_markup=menu_keyboard)
    elif update.effective_chat and user_id:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=reminder_text,
                reply_markup=menu_keyboard,
            )
        except TelegramError as error:
            logger.warning(
                "Не удалось отправить напоминание без текстового сообщения: %s",
                error,
            )
    else:
        logger.warning("Получено сообщение без состояния и информации о чате.")


@handle_errors
@user_bootstrap
async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user: Optional[User],
    is_new_user: bool,
) -> None:
    user = update.effective_user
    admin_state = _get_admin_state(context)
    if user and str(user.id) == settings.ADMIN_CHAT_ID and admin_state != AdminState.DEFAULT:
        await handle_admin_message(update, context)
        return

    state = _get_user_state(context)

    if state is UserState.CHATGPT_STREAMING:
        if update.message and update.message.text == "Закончить диалог":
            await stop_chatgpt_session(update, context)
        else:
            wait_text = "Пожалуйста, подождите, пока я закончу отвечать на предыдущий запрос."
            if update.message and hasattr(update.message, "reply_text"):
                await update.message.reply_text(wait_text)
            elif update.effective_chat:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=wait_text)
        return

    if state is UserState.CHATGPT_ACTIVE:
        await _handle_chatgpt_message(update, context)
        return

    if state is UserState.SUPPORT_LLM_ACTIVE:
        await _handle_support_llm_message(update, context)
        return

    if state is UserState.AWAITING_SUPPORT_MESSAGE:
        await _handle_manual_support_message(update, context)
        return

    if state is UserState.AWAITING_VERIFICATION_ID:
        await handle_id_submission(update, context)
        return

    if db_user and db_user.awaiting_verification:
        await handle_id_submission(update, context)
        return

    await _send_main_menu_reminder(update, context, user.id if user else None)

async def _cancel_active_chatgpt_streams(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Останавливает все активные генераторы ответов ChatGPT."""

    active_streams: Optional[Set[Any]] = context.user_data.get("_chatgpt_active_streams")
    if not active_streams:
        return False

    cancelled_any = False
    for stream in list(active_streams):
        close = getattr(stream, "aclose", None)
        if callable(close):
            try:
                await close()
                cancelled_any = True
            except RuntimeError:
                # Генератор уже закрыт — игнорируем.
                pass
            except Exception as error:  # pragma: no cover - логируем для диагностики
                logger.warning("Не удалось корректно закрыть поток ChatGPT: %s", error)
        active_streams.discard(stream)

    if not active_streams:
        context.user_data.pop("_chatgpt_active_streams", None)

    return cancelled_any


async def _perform_chatgpt_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Останавливает текущую сессию ChatGPT и возвращает пользователя в главное меню."""

    context.user_data["_chatgpt_cancelled_by_user"] = True

    await _cancel_active_chatgpt_streams(context)

    _set_default_state(context)

    context.user_data.pop("chat_history", None)

    if update.message is None:
        return

    user = update.effective_user
    keyboard = get_main_menu_keyboard(user.id) if user else None

    await update.message.reply_text(
        "Диалог завершен. Вы вернулись в главное меню.",
        reply_markup=keyboard,
    )
