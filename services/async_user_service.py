"""Асинхронные user-related service utilities."""
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from db_async_session import get_async_db
from models.async_crud import create_user, get_user
from models.user import User


async def get_or_create_user(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> tuple[Optional[User], bool]:
    """Fetches a user from the database or creates a new record."""
    effective_user = update.effective_user
    if effective_user is None:
        return None, False

    async for db in get_async_db():
        db_user: Optional[User] = await get_user(db, effective_user.id)
        if db_user is not None:
            return db_user, False

        db_user = await create_user(
            db,
            {
                "id": effective_user.id,
                "username": effective_user.username,
                "full_name": effective_user.full_name,
            },
        )
        return db_user, True


__all__ = ["get_or_create_user"]