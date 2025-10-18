"""User-related service utilities."""

from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from config import get_settings
from db_session import get_db
from models.crud import create_user, get_user
from models.user import User
from services.notifier import Notifier

settings = get_settings()
logger = settings.logger


async def get_or_create_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> Optional[User]:
    """Fetches a user from the database or creates a new record."""

    effective_user = update.effective_user
    if effective_user is None:
        return None

    try:
        from handlers import decorators as handler_decorators  # type: ignore
    except ImportError:
        handler_decorators = None

    get_db_fn = getattr(handler_decorators, "get_db", get_db)
    get_user_fn = getattr(handler_decorators, "get_user", get_user)
    create_user_fn = getattr(handler_decorators, "create_user", create_user)

    with get_db_fn() as db:
        db_user: Optional[User] = get_user_fn(db, effective_user.id)
        if db_user is not None:
            return db_user

        db_user = create_user_fn(
            db,
            {
                "id": effective_user.id,
                "username": effective_user.username,
                "full_name": effective_user.full_name,
            },
        )

    logger.info(
        "Новый пользователь: %s (%s) @%s",
        effective_user.id,
        effective_user.full_name,
        effective_user.username,
    )

    notifier = Notifier(context.bot)
    user_fullname = escape_markdown(
        effective_user.full_name or "Имя не указано", version=2
    )
    user_username = (
        "@" + escape_markdown(effective_user.username, version=2)
        if effective_user.username
        else "Нет"
    )
    admin_message = (
        "👋 Новый пользователь!\n\n"
        + "Имя: {fullname}\nUsername: {username}\nID: `{user_id}`".format(
            fullname=user_fullname,
            username=user_username,
            user_id=effective_user.id,
        )
    )
    await notifier.send_admin_notification(
        admin_message,
        parse_mode="MarkdownV2",
    )

    return db_user


__all__ = ["get_or_create_user"]
