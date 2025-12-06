"""Admin handlers for user lookup, messaging, and approvals."""

from __future__ import annotations

from __future__ import annotations

from datetime import datetime
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from config import get_settings
from db_session import get_db
from models.crud import (
    get_user,
    get_user_by_username,
)
from services.notifier import Notifier
from services.state_manager import StateManager

settings = get_settings()
logger = settings.logger


async def handle_user_lookup(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    get_db_fn=get_db,
    get_user_fn=get_user,
    get_user_by_username_fn=get_user_by_username,
    display_user_card_fn=None,
) -> None:
    message = update.message
    if message is None:
        return

    target_id_str = (message.text or "").strip()
    state_manager = StateManager(context)
    state_manager.reset_admin_state()

    with get_db_fn() as db:
        if target_id_str.isdigit():
            found_user = get_user_fn(db, int(target_id_str))
        else:
            cleaned_username = target_id_str.replace("@", "").lower()
            found_user = get_user_by_username_fn(db, cleaned_username)

    if found_user:
        card_callable = display_user_card_fn or display_user_card
        await card_callable(update, context, found_user.user_id)
    else:
        await message.reply_text(f"❌ Пользователь '{target_id_str}' не найден.")


async def handle_direct_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    target_user_id = context.user_data.pop("dm_target_user_id", None)
    reply_to_message_id = context.user_data.pop("reply_to_message_id", None)
    state_manager = StateManager(context)
    state_manager.reset_admin_state()

    if not target_user_id:
        await message.reply_text("❌ Не удалось определить пользователя для ответа.")
        return

    text_to_send = message.text or ""
    send_kwargs = {
        "chat_id": target_user_id,
        "text": text_to_send,
        "reply_markup": InlineKeyboardMarkup(
            [[InlineKeyboardButton("✍️ Ответить", callback_data="support_from_dm")]]
        ),
    }
    if reply_to_message_id is not None:
        send_kwargs["reply_to_message_id"] = reply_to_message_id

    notifier = Notifier(context.bot)
    sent_message = await notifier.send_message(**send_kwargs)

    if sent_message is None:
        await message.reply_text(
            "❌ Не удалось отправить сообщение пользователю. Возможно, он заблокировал бота."
        )
    else:
        await message.reply_text("✅ Сообщение успешно отправлено!")


async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deprecated - use subscription system instead."""
    if str(update.effective_user.id) != settings.ADMIN_CHAT_ID:
        return
    
    await update.message.reply_text(
        "⚠️ Функция /approve устарела.\n\n"
        "Используйте систему подписок:\n"
        "/grant_sub <user_id> <days>"
    )


async def reset_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Функция сброса пользователя требует обновления для работы с БД."
    )


async def display_user_card(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
) -> None:
    with get_db() as db:
        db_user = get_user(db, user_id)

    if not db_user:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                f"Пользователь с ID {user_id} не найден в базе данных."
            )
        else:
            await update.message.reply_text(
                f"Пользователь с ID {user_id} не найден в базе данных."
            )
        return

    # Subscription-based status
    status = (
        "🚫 Заблокирован"
        if db_user.is_banned
        else "✅ Активен"
    )

    first_seen_str = (
        db_user.first_seen.strftime("%d.%m.%Y %H:%M") if db_user.first_seen else "Неизвестно"
    )
    last_seen_str = (
        db_user.last_seen.strftime("%d.%m.%Y %H:%M") if db_user.last_seen else "Неизвестно"
    )

    safe_name = escape_markdown(db_user.full_name or "Неизвестно", version=2)
    safe_user = escape_markdown(db_user.username or "Нет", version=2)

    card_text = (
        "👤 *Карточка пользователя*\n\n"
        f"*ID:* `{db_user.user_id}`\n*Имя:* {safe_name}\n*Username:* @{safe_user}\n\n"
        f"*Статус:* {status}\n*Первый визит:* {escape_markdown(first_seen_str, version=2)}\n"
        f"*Активность:* {escape_markdown(last_seen_str, version=2)}"
    )

    try:
        admin_chat_id = int(settings.ADMIN_CHAT_ID)
    except (TypeError, ValueError):
        admin_chat_id = None

    allow_sensitive_actions = admin_chat_id is None or user_id != admin_chat_id

    action_buttons = []
    # Deprecated: approval system removed

    if allow_sensitive_actions:
        if db_user.is_banned:
            action_buttons.append(
                InlineKeyboardButton("✅ Разблок", callback_data=f"user_unblock_{user_id}")
            )
        else:
            action_buttons.append(
                InlineKeyboardButton("🚫 Заблок", callback_data=f"user_block_{user_id}")
            )

        action_buttons.append(
            InlineKeyboardButton("Удалить 🧨", callback_data=f"user_delete_{user_id}")
        )

    keyboard = [action_buttons] if action_buttons else []
    keyboard.append(
        [InlineKeyboardButton("💬 Написать", callback_data=f"user_message_{user_id}")]
    )
    keyboard.append(
        [
            InlineKeyboardButton("⬅️ Новый поиск", callback_data="admin_users"),
            InlineKeyboardButton("⬅️ В админку", callback_data="admin_main"),
        ]
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            card_text,
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        chat = update.effective_chat
        if chat is not None:
            notifier = Notifier(context.bot)
            await notifier.send_message(
                chat_id=chat.id,
                text=card_text,
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )


__all__ = [
    "handle_user_lookup",
    "handle_direct_message",
    "display_user_card",
    "approve_user",
    "reset_user",
]
