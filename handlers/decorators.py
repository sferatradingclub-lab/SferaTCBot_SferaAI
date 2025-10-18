"""Декораторы для обработчиков Telegram-бота."""

from functools import wraps
from typing import Any, Awaitable, Callable, Optional, TypeVar, cast

from telegram import Update
from telegram.ext import ContextTypes

from db_session import get_db
from models.crud import create_user, get_user, update_user_last_seen
from models.user import User
from services.user_service import get_or_create_user

HandlerFunc = TypeVar("HandlerFunc", bound=Callable[..., Awaitable[Any]])


def user_bootstrap(func: HandlerFunc) -> HandlerFunc:
    """Оборачивает обработчик логикой инициализации и проверки пользователя."""

    @wraps(func)
    async def wrapper(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        user = update.effective_user
        if user is None:
            handler_kwargs = {**kwargs, "db_user": None, "is_new_user": False}
            return await func(update, context, *args, **handler_kwargs)

        db_user = await get_or_create_user(update, context)
        if db_user is None or db_user.is_banned:
            return None

        with get_db() as db:
            update_user_last_seen(db, user.id)
            refreshed_user: Optional[User] = get_user(db, user.id)
            if refreshed_user is not None:
                db_user = refreshed_user

        handler_kwargs = {**kwargs, "db_user": db_user, "is_new_user": False}
        return await func(update, context, *args, **handler_kwargs)

    return cast(HandlerFunc, wrapper)
