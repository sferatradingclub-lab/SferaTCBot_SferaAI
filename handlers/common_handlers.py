from typing import Any, Awaitable, Callable, Dict, List, Optional

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from config import (
    ADMIN_CHAT_ID,
    CHATGPT_IMAGE_URL,
    PSYCHOLOGIST_IMAGE_URL,
    SUPPORT_ESCALATION_BUTTON_TEXT,
    SUPPORT_IMAGE_URL,
    SUPPORT_LLM_HISTORY_LIMIT,
    SUPPORT_LLM_SYSTEM_PROMPT,
    TRAINING_IMAGE_URL,
    WELCOME_IMAGE_URL,
    get_safe_url,
    logger,
)
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


def _default_chat_history() -> List[Dict[str, str]]:
    return [{"role": "system", "content": CHATGPT_SYSTEM_PROMPT}]


def _normalize_chat_history(raw_history: Any) -> List[Dict[str, str]]:
    if not isinstance(raw_history, list):
        if raw_history is not None:
            logger.warning(
                "История чата имела некорректный тип %s. Переинициализация истории.",
                type(raw_history),
            )
        return _default_chat_history()

    normalized_history: List[Dict[str, str]] = []

    for entry in raw_history:
        if not isinstance(entry, dict):
            logger.warning("Пропускаю некорректную запись истории типа %s", type(entry))
            continue

        role = entry.get("role")
        content = entry.get("content")

        if isinstance(role, str) and isinstance(content, str):
            normalized_history.append({"role": role, "content": content})
        else:
            logger.warning("Пропускаю запись истории без корректных полей role/content: %s", entry)

    if not normalized_history:
        return _default_chat_history()

    if normalized_history[0].get("role") != "system":
        logger.warning("В истории отсутствует системное сообщение. Переинициализация истории.")
        return _default_chat_history()

    return normalized_history


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
            "👋 Новый пользователь!\n\n"
            f"Имя: {user_fullname}\nUsername: {user_username}\nID: `{user.id}`"
        )
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
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
    welcome_photo_url = get_safe_url(WELCOME_IMAGE_URL, "welcome_image")
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
        training_photo_url = get_safe_url(TRAINING_IMAGE_URL, "training_image")
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

    psychologist_photo_url = get_safe_url(PSYCHOLOGIST_IMAGE_URL, "psychologist_image")
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
    context.user_data["chat_history"] = _default_chat_history()

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
    context.user_data.pop("chat_history", None)
    _set_default_state(context)

    if update.message is None:
        return

    await update.message.reply_text(
        "Диалог завершен. Вы вернулись в главное меню.",
        reply_markup=get_main_menu_keyboard(update.effective_user.id),
    )


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
        {"role": "system", "content": SUPPORT_LLM_SYSTEM_PROMPT}
    ]

    if update.message is None:
        return

    support_caption = (
        "Я — ИИ-поддержка SferaTC и готов помочь. Опишите проблему текстом, а если понадобится человек, "
        f"нажмите кнопку «{SUPPORT_ESCALATION_BUTTON_TEXT}»."
    )
    support_photo_url = get_safe_url(SUPPORT_IMAGE_URL, "support_image")
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

    if message is None or not getattr(message, "text", None):
        prompt_text = (
            "Пожалуйста, отправьте текстовое сообщение для ИИ-ассистента "
            "или завершите диалог с помощью кнопки ниже."
        )

        if message and hasattr(message, "reply_text"):
            await message.reply_text(prompt_text, reply_markup=get_chatgpt_keyboard())
        elif update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=prompt_text,
                    reply_markup=get_chatgpt_keyboard(),
                )
            except TelegramError as error:
                logger.warning(
                    "Не удалось отправить подсказку без текстового сообщения: %s",
                    error,
                )
        else:
            logger.warning("Получено сообщение без текста и информации о чате.")

        return

    if message.text == "Закончить диалог":
        await stop_chatgpt_session(update, context)
        return

    history = _normalize_chat_history(context.user_data.get("chat_history"))
    history.append({"role": "user", "content": message.text})

    if len(history) > 11:
        history = [history[0]] + history[-10:]

    context.user_data["chat_history"] = history

    response_text = await get_chatgpt_response(
        history,
        context.application,
    )

    if response_text and response_text.strip():
        context.user_data["chat_history"].append({"role": "assistant", "content": response_text})
        await update.message.reply_text(
            response_text,
            reply_markup=get_chatgpt_keyboard(),
        )
    else:
        logger.warning("Модель вернула пустой или некорректный ответ.")
        await update.message.reply_text(
            "Мне не удалось сгенерировать ответ. Попробуйте переформулировать ваш запрос.",
            reply_markup=get_chatgpt_keyboard(),
        )


async def _handle_support_llm_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.message
    text = (message.text or "").strip() if message else ""

    if text.lower() == SUPPORT_ESCALATION_BUTTON_TEXT.lower():
        await _activate_manual_support(context, message.reply_text)  # type: ignore[arg-type]
        return

    if not text:
        if message:
            await message.reply_text(
                "ИИ-поддержка сейчас работает только с текстовыми сообщениями. "
                f"Опишите вопрос словами или нажмите «{SUPPORT_ESCALATION_BUTTON_TEXT}».",
                reply_markup=get_support_llm_keyboard(),
            )
        return

    history = context.user_data.get("support_llm_history") or [
        {"role": "system", "content": SUPPORT_LLM_SYSTEM_PROMPT}
    ]
    history = history + [{"role": "user", "content": text}]

    if len(history) > SUPPORT_LLM_HISTORY_LIMIT + 1:
        history = [history[0]] + history[-SUPPORT_LLM_HISTORY_LIMIT:]

    context.user_data["support_llm_history"] = history
    response_text = await get_chatgpt_response(
        history,
        context.application,
    )

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
                f"{SUPPORT_ESCALATION_BUTTON_TEXT}».",
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
    if user and str(user.id) == ADMIN_CHAT_ID and admin_state != AdminState.DEFAULT:
        await handle_admin_message(update, context)
        return

    state = _get_user_state(context)

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

