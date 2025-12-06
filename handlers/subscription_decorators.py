"""Subscription-related decorators for handlers."""

from functools import wraps
from typing import Callable, Any

from telegram import Update
from telegram.ext import ContextTypes

from services.subscription_service import check_access, get_user_tier, format_usage_stats


def require_subscription(min_tier: str = "free"):
    """
    Decorator to check subscription tier before executing handler.
    
    Usage:
        @require_subscription("pro")
        async def some_handler(update, context, db_user):
            ...
    
    Args:
        min_tier: Minimum tier required ("free" or "pro")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            if not user:
                return await func(update, context, *args, **kwargs)
            
            user_tier = get_user_tier(user.id)
            
            tier_order = {"free": 0, "pro": 1}
            
            if tier_order.get(user_tier, 0) < tier_order.get(min_tier, 0):
                message = (
                    f"❌ Эта функция требует <b>{min_tier.capitalize()}</b> подписку.\n\n"
                    f"Ваш текущий тариф: <b>{user_tier.capitalize()}</b>\n\n"
                    f"Обновитесь сейчас: /subscribe"
                )
                
                if update.message:
                    await update.message.reply_text(message, parse_mode="HTML")
                elif update.callback_query:
                    await update.callback_query.answer(
                        f"Требуется {min_tier.capitalize()} подписка",
                        show_alert=True
                    )
                
                return None
            
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    return decorator


def check_feature_access(feature: str):
    """
    Decorator to check access to specific features (KB, web search).
    
    Usage:
        @check_feature_access("search_kb")
        async def knowledge_base_handler(update, context):
            ...
    
    Args:
        feature: Feature to check ("search_kb", "search_web")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            if not user:
                return await func(update, context, *args, **kwargs)
            
            can_access, reason = check_access(user.id, feature)
            
            if not can_access:
                if update.message:
                    await update.message.reply_text(reason, parse_mode="HTML")
                elif update.callback_query:
                    await update.callback_query.answer(
                        "Требуется Pro подписка",
                        show_alert=True
                    )
                return None
            
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    return decorator


async def send_usage_stats(update: Update, user_id: int) -> None:
    """
    Send usage statistics to user.
    
    Helper function to show current usage and limits.
    """
    stats = format_usage_stats(user_id)
    
    if update.message:
        await update.message.reply_text(stats, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.message.reply_text(stats, parse_mode="HTML")
