"""Subscription and access control service."""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, Tuple
import logging

from db_session import get_db
from models.subscription_crud import (
    get_user_subscription,
    get_or_create_today_usage,
    increment_session_count,
    add_session_duration,
    create_free_subscription,
)

logger = logging.getLogger(__name__)


@dataclass
class TierLimits:
    """Limits configuration for each tier."""
    sessions_per_day: Optional[int]  # None = unlimited
    minutes_per_session: Optional[int]  # None = unlimited
    allow_knowledge_base: bool
    allow_web_search: bool
    priority: int  # 1-2 (higher = better LiveKit priority)


# Tier configuration based on user requirements
TIER_CONFIG = {
    "free": TierLimits(
        sessions_per_day=3,
        minutes_per_session=10,
        allow_knowledge_base=True,  # Free tier has KB access
        allow_web_search=True,  # Free tier has web search
        priority=1
    ),
    "pro": TierLimits(
        sessions_per_day=None,  # Unlimited
        minutes_per_session=None,  # Unlimited
        allow_knowledge_base=True,
        allow_web_search=True,
        priority=2
    ),
}


def get_user_tier(user_id: int) -> str:
    """
    Get user's current tier.
    
    Returns: "free" or "pro"
    """
    with get_db() as db:
        subscription = get_user_subscription(db, user_id)
        
        if not subscription:
            # User doesn't have subscription yet - create free tier
            logger.info(f"User {user_id} has no subscription, creating free tier")
            subscription = create_free_subscription(db, user_id)
            return "free"
        
        tier = subscription.get_tier()
        logger.debug(f"User {user_id} tier: {tier}")
        return tier


def check_access(user_id: int, action: str) -> Tuple[bool, str]:
    """
    Check if user can perform action based on subscription.
    
    Args:
        user_id: Telegram user ID
        action: One of "start_session", "search_kb", "search_web"
    
    Returns:
        (allowed: bool, reason: str) - reason is empty if allowed
    """
    tier = get_user_tier(user_id)
    limits = TIER_CONFIG[tier]
    
    if action == "start_session":
        # Check daily session limit
        if limits.sessions_per_day is None:
            return True, ""  # Unlimited
        
        with get_db() as db:
            usage = get_or_create_today_usage(db, user_id)
            
            if usage.sessions_today >= limits.sessions_per_day:
                return False, (
                    f"❌ Достигнут дневной лимит ({limits.sessions_per_day} сессий).\n\n"
                    f"💎 Обновитесь до Pro для безлимитного доступа!\n"
                    f"👉 /subscribe"
                )
            
            return True, ""
    
    elif action == "search_kb":
        if not limits.allow_knowledge_base:
            return False, (
                "❌ Доступ к базе знаний требует Pro подписку.\n"
                "👉 /subscribe"
            )
        return True, ""
    
    elif action == "search_web":
        if not limits.allow_web_search:
            return False, (
                "❌ Веб-поиск требует Pro подписку.\n"
                "👉 /subscribe"
            )
        return True, ""
    
    else:
        logger.warning(f"Unknown action: {action}")
        return True, ""  # Default allow for unknown actions


async def track_session_start(user_id: int) -> Tuple[bool, str]:
    """
    Track session start and check if allowed.
    
    Returns:
        (allowed: bool, reason: str)
    """
    # Check if user can start session
    can_start, reason = check_access(user_id, "start_session")
    
    if not can_start:
        return False, reason
    
    # Increment session counter
    with get_db() as db:
        increment_session_count(db, user_id)
    
    logger.info(f"Session started for user {user_id}")
    return True, ""


async def track_session_end(user_id: int, duration_minutes: float) -> None:
    """
    Track session end and update usage.
    
    Args:
        user_id: Telegram user ID
        duration_minutes: Session duration in minutes
    """
    with get_db() as db:
        add_session_duration(db, user_id, duration_minutes)
    
    logger.info(f"Session ended for user {user_id}, duration: {duration_minutes:.2f} min")


def get_tier_limits(user_id: int) -> TierLimits:
    """Get tier limits for user."""
    tier = get_user_tier(user_id)
    return TIER_CONFIG[tier]


def get_remaining_sessions_today(user_id: int) -> Optional[int]:
    """
    Get remaining sessions for today.
    
    Returns:
        Number of remaining sessions, or None if unlimited
    """
    tier = get_user_tier(user_id)
    limits = TIER_CONFIG[tier]
    
    if limits.sessions_per_day is None:
        return None  # Unlimited
    
    with get_db() as db:
        usage = get_or_create_today_usage(db, user_id)
        remaining = limits.sessions_per_day - usage.sessions_today
        return max(0, remaining)


def format_usage_stats(user_id: int) -> str:
    """
    Format usage statistics for user.
    
    Returns:
        Formatted string with usage info
    """
    tier = get_user_tier(user_id)
    limits = TIER_CONFIG[tier]
    
    with get_db() as db:
        usage = get_or_create_today_usage(db, user_id)
    
    if tier == "pro":
        return (
            "💎 <b>Pro подписка</b>\n\n"
            f"Сегодня использовано:\n"
            f"• Сессий: {usage.sessions_today} (безлимит)\n"
            f"• Время: {usage.minutes_today:.1f} мин (безлимит)\n"
        )
    else:
        remaining_sessions = limits.sessions_per_day - usage.sessions_today
        remaining_minutes = (limits.minutes_per_session * limits.sessions_per_day) - usage.minutes_today
        
        return (
            "🆓 <b>Free подписка</b>\n\n"
            f"Сегодня использовано:\n"
            f"• Сессий: {usage.sessions_today}/{limits.sessions_per_day}\n"
            f"• Время: {usage.minutes_today:.1f} мин\n\n"
            f"Осталось:\n"
            f"• Сессий: {max(0, remaining_sessions)}\n"
            f"• Время: ~{max(0, remaining_minutes):.0f} мин\n\n"
            f"💡 Обновитесь до Pro для безлимитного доступа:\n"
            f"/subscribe"
        )


def check_session_timeout(user_id: int, elapsed_minutes: float) -> Tuple[bool, str]:
    """
    Check if session should be terminated due to timeout.
    
    Args:
        user_id: Telegram user ID
        elapsed_minutes: Minutes elapsed since session start
    
    Returns:
        (should_end: bool, message: str)
    """
    tier = get_user_tier(user_id)
    limits = TIER_CONFIG[tier]
    
    if limits.minutes_per_session is None:
        return False, ""  # No timeout for unlimited
    
    if elapsed_minutes >= limits.minutes_per_session:
        return True, (
            f"⏱️ Время сессии истекло ({limits.minutes_per_session} мин).\n\n"
            f"💎 Обновитесь до Pro для безлимитного времени!\n"
            f"/subscribe"
        )
    
    # Warning at 80% of time
    warning_threshold = limits.minutes_per_session * 0.8
    if elapsed_minutes >= warning_threshold:
        remaining = limits.minutes_per_session - elapsed_minutes
        return False, f"⚠️ Осталось {remaining:.1f} мин"
    
    return False, ""
