"""Base user handlers that route messages across bot subsystems."""

from __future__ import annotations

from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from config import get_safe_url, get_settings
from keyboards import (
    get_channel_keyboard,
    get_main_menu_keyboard,
    get_psychologist_keyboard,
    get_training_keyboard,
)
from models.user import User
from services.notifier import Notifier
from services.state_manager import StateManager

from .admin_handlers import handle_admin_message
from .decorators import user_bootstrap
from .error_handler import handle_errors
from .states import AdminState, UserState
from .verification_handlers import (
    handle_id_submission,
    start_verification_process,
)
from .user.chatgpt_handler import handle_chatgpt_message, handle_streaming_state
from .user.support_handler import handle_manual_support_message, handle_support_llm_message

settings = get_settings()
logger = settings.logger

FRIENDLY_MAIN_MENU_REMINDER = "Выберите действие в меню ниже:"


@handle_errors
@user_bootstrap
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user: Optional[User],
    **_: object,
) -> None:
    user = update.effective_user
    state_manager = StateManager(context)

    payload = " ".join(context.args)
    if payload == "trial_completed":
        state_manager.set_user_state(UserState.AWAITING_VERIFICATION_ID)
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
        FRIENDLY_MAIN_MENU_REMINDER,
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
        notifier = Notifier(context.bot)
        await notifier.send_message(
            chat_id=update.effective_chat.id,
            text=reminder_text,
            reply_markup=menu_keyboard,
        )
    else:
        logger.warning("Получено ссообщение без состояния и информации о чате.")


@handle_errors
@user_bootstrap
async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_user: Optional[User],
    is_new_user: bool,
) -> None:
    user = update.effective_user
    state_manager = StateManager(context)

    admin_state = state_manager.get_admin_state()
    if user and str(user.id) == settings.ADMIN_CHAT_ID and admin_state != AdminState.DEFAULT:
        await handle_admin_message(update, context)
        return

    state = state_manager.get_user_state()

    if state is UserState.CHATGPT_STREAMING:
        await handle_streaming_state(update, context)
        return

    if state is UserState.CHATGPT_ACTIVE:
        await handle_chatgpt_message(update, context)
        return

    if state is UserState.SUPPORT_LLM_ACTIVE:
        await handle_support_llm_message(update, context)
        return

    if state is UserState.AWAITING_SUPPORT_MESSAGE:
        await handle_manual_support_message(update, context)
        return

    if state is UserState.AWAITING_VERIFICATION_ID:
        await handle_id_submission(update, context)
        return

    if db_user and db_user.awaiting_verification:
        await handle_id_submission(update, context)
        return

    await _send_main_menu_reminder(update, context, user.id if user else None)


__all__ = [
    "start",
    "show_training_menu",
    "show_psychologist_menu",
    "help_command",
    "handle_message",
]
