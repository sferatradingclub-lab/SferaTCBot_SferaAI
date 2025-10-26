"""Handlers responsible for the user-facing support experience."""


from __future__ import annotations

from typing import Awaitable, Callable

from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from config import get_safe_url, get_settings, send_video_or_photo_fallback, get_video_or_photo_urls
from keyboards import (
    get_main_menu_keyboard,
    get_support_llm_keyboard,
)
from services.chatgpt_service import get_chatgpt_response
from services.state_manager import StateManager
from handlers.decorators import user_bootstrap
from handlers.error_handler import handle_errors
from handlers.states import UserState
from handlers.verification_handlers import handle_support_message

settings = get_settings()
logger = settings.logger

SupportPromptSender = Callable[[str], Awaitable[object]]
SUPPORT_ESCALATION_PROMPT = "Опишите вашу проблему одним сообщением, и мы передадим его администратору."


def _ensure_manual_support_state(context: ContextTypes.DEFAULT_TYPE) -> bool:
    state_manager = StateManager(context)
    already_manual = state_manager.get_user_state() == UserState.AWAITING_SUPPORT_MESSAGE
    state_manager.set_user_state(UserState.AWAITING_SUPPORT_MESSAGE)
    return not already_manual


async def _activate_manual_support(
    context: ContextTypes.DEFAULT_TYPE,
    prompt_sender: SupportPromptSender,
) -> None:
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


@handle_errors
@user_bootstrap
async def show_support_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user,
    is_new_user: bool,
) -> None:
    state_manager = StateManager(context)
    state_manager.set_user_state(UserState.SUPPORT_LLM_ACTIVE)
    context.user_data["support_llm_history"] = [
        {"role": "system", "content": settings.SUPPORT_LLM_SYSTEM_PROMPT}
    ]

    if update.message is None:
        return

    support_caption = (
        "Я — ИИ-поддержка SferaTC и готов помочь. Опишите проблему текстом, а если понадобится человек, "
        f"нажмите кнопку «{settings.SUPPORT_ESCALATION_BUTTON_TEXT}»."
    )
    # Используем отдельные переменные для видео и изображения
    support_video_url, support_photo_url = get_video_or_photo_urls(settings, "SUPPORT")
    
    await send_video_or_photo_fallback(
        message=update.message,
        video_url=support_video_url,
        photo_url=support_photo_url,
        caption=support_caption,
        reply_markup=get_support_llm_keyboard()
    )


@handle_errors
@user_bootstrap
async def escalate_support_to_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user,
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


async def handle_support_llm_message(
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


async def handle_manual_support_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    message = update.message
    if message is None:
        return

    if message.text == "Вернуться в меню":
        state_manager = StateManager(context)
        state_manager.reset_user_state()
        await message.reply_text(
            "Вы вернулись в главное меню.",
            reply_markup=get_main_menu_keyboard(update.effective_user.id),
        )
        return

    await handle_support_message(update, context)


__all__ = [
    "show_support_menu",
    "escalate_support_to_admin",
    "handle_support_llm_message",
    "handle_manual_support_message",
]
