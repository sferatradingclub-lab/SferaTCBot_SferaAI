"""Декораторы для обработчиков Telegram-бота."""

from functools import wraps
from typing import Any, Awaitable, Callable, Optional, TypeVar, cast

from telegram import Update
from telegram.ext import ContextTypes

from db_session import get_db
from models.crud import create_user, get_user, update_user_last_seen
from models.user import User

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

        with get_db() as db:
            db_user: Optional[User] = get_user(db, user.id)
            is_new_user = False

            if db_user is None:
                db_user = create_user(
                    db,
                    {
                        "id": user.id,
                        "username": user.username,
                        "full_name": user.full_name,
                    },
                )
                is_new_user = True

            if db_user.is_banned:
                return None

            update_user_last_seen(db, user.id)

            handler_kwargs = {**kwargs, "db_user": db_user, "is_new_user": is_new_user}
            return await func(update, context, *args, **handler_kwargs)

    return cast(HandlerFunc, wrapper)

