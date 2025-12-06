"""Декораторы для обработчиков Telegram-бота."""

from functools import wraps
from typing import Any, Awaitable, Callable, Optional, TypeVar, cast

from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

from config import get_settings
from db_session import get_db
from models.crud import create_user, get_user, update_user_last_seen
from models.user import User
from services.notifier import Notifier
from services.user_service import get_or_create_user

HandlerFunc = TypeVar("HandlerFunc", bound=Callable[..., Awaitable[Any]])

settings = get_settings()
logger = settings.logger


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

        logger.info(f"Обработка пользователя: {user.id} ({user.full_name}) @{user.username}")
        
        # Шаг 1: Получаем или создаем пользователя
        logger.info(f"Вызов get_or_create_user для пользователя {user.id}")
        db_user, is_new_user = await get_or_create_user(update, context)
        
        logger.info(f"Результат get_or_create_user: db_user={db_user is not None}, is_new_user={is_new_user}")
        
        if db_user is None:
            logger.error(f"get_or_create_user вернул None для пользователя {user.id}")
            handler_kwargs = {**kwargs, "db_user": None, "is_new_user": False}
            return await func(update, context, *args, **handler_kwargs)
        
        # NEW: Create free subscription for new users
        if is_new_user:
            from models.subscription_crud import get_user_subscription, create_free_subscription
            with get_db() as db:
                subscription = get_user_subscription(db, user.id)
                if not subscription:
                    create_free_subscription(db, user.id)
                    logger.info(f"Created Free tier subscription for new user {user.id}")
            
        if db_user.is_banned:
            logger.info(f"Пользователь {user.id} заблокирован, пропускаем обработку")
            return None

        # Шаг 2: Обрабатываем нового пользователя
        if is_new_user:
            logger.info(
                f"ПОДТВЕРЖДЕНО: Новый пользователь: {user.id} ({user.full_name}) @{user.username}"
            )
            
            # Проверяем настройки админского чата
            admin_chat_id = settings.ADMIN_CHAT_ID
            logger.info(f"ADMIN_CHAT_ID из настроек: {admin_chat_id} (тип: {type(admin_chat_id)})")
            
            if not admin_chat_id:
                logger.error("ADMIN_CHAT_ID не настроен!")
                handler_kwargs = {**kwargs, "db_user": db_user, "is_new_user": is_new_user}
                return await func(update, context, *args, **handler_kwargs)
            
            # Проверяем бота
            bot = context.bot
            logger.info(f"Бот инициализирован: {bot is not None}")
            
            if bot is None:
                logger.error("Бот не инициализирован!")
                handler_kwargs = {**kwargs, "db_user": db_user, "is_new_user": is_new_user}
                return await func(update, context, *args, **handler_kwargs)
            
            # Создаем уведомление
            notifier = Notifier(bot)
            user_fullname = escape_markdown(
                user.full_name or "Имя не указано", version=2
            )
            user_username = (
                "@" + escape_markdown(user.username, version=2)
                if user.username
                else "Нет"
            )
            admin_message = (
                "👋 Новый пользователь\\!\n\n"
                + "Имя: {fullname}\nUsername: {username}\nID: `{user_id}`".format(
                    fullname=user_fullname,
                    username=user_username,
                    user_id=user.id,
                )
            )
            
            logger.info(f"Подготовлено сообщение для админа: {admin_message[:100]}...")
            
            # Шаг 3: Отправляем уведомление
            try:
                logger.info(f"Попытка отправить уведомление админу о пользователе {user.id}")
                result = await notifier.send_admin_notification(
                    admin_message,
                    parse_mode="MarkdownV2",
                )
                
                if result is None:
                    logger.error(
                        f"КРИТИЧНО: Не удалось отправить уведомление админу о новом пользователе {user.id}. "
                        f"Результат send_admin_notification = None"
                    )
                else:
                    logger.info(
                        f"УСПЕХ: Уведомление о новом пользователе {user.id} успешно отправлено админу. "
                        f"Message ID: {result.message_id}"
                    )
                    
            except Exception as e:
                logger.error(
                    f"КРИТИЧНО: Исключение при отправке уведомления админу о пользователе {user.id}: {e}",
                    exc_info=True
                )
        else:
            logger.info(f"Пользователь {user.id} уже существует в базе данных")

        # Шаг 4: Обновляем last_seen и получаем свежие данные пользователя
        logger.info(f"Обновление last_seen для пользователя {user.id}")
        with get_db() as db:
            update_user_last_seen(db, user.id)
            refreshed_user: Optional[User] = get_user(db, user.id)
            if refreshed_user is not None:
                db_user = refreshed_user
                logger.info(f"Пользователь {user.id} успешно обновлен в базе данных")
            else:
                logger.warning(f"Не удалось обновить пользователя {user.id} в базе данных")

        handler_kwargs = {**kwargs, "db_user": db_user, "is_new_user": is_new_user}
        logger.info(f"Вызов обработчика {func.__name__} с параметрами: db_user={db_user is not None}, is_new_user={is_new_user}")
        return await func(update, context, *args, **handler_kwargs)

    return cast(HandlerFunc, wrapper)
