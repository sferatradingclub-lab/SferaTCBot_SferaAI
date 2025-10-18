"""User-related service utilities."""

from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from db_session import get_db
from models.crud import create_user, get_user
from models.user import User


async def get_or_create_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[Optional[User], bool]:
    """Fetches a user from the database or creates a new record."""

    effective_user = update.effective_user
    if effective_user is None:
        return None, False

    with get_db() as db:
        db_user: Optional[User] = get_user(db, effective_user.id)
        if db_user is not None:
            return db_user, False

        db_user = create_user(
            db,
            {
                "id": effective_user.id,
                "username": effective_user.username,
                "full_name": effective_user.full_name,
            },
        )
        return db_user, True


__all__ = ["get_or_create_user"]
