"""Subscription activation after payment completion."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from db_session import get_db
from models.subscription_crud import (
    get_user_subscription,
    create_pro_subscription,
    record_promo_usage,
)
from models.subscription_crud import get_promo_code
from models.payment import PaymentStatus

logger = logging.getLogger(__name__)


async def activate_subscription_from_payment(
    user_id: int,
    tier: str,
    payment_id: int,
    promo_code: Optional[str] = None,
    duration_days: int = 30
) -> bool:
    """
    Activate subscription after successful payment.
    
    Args:
        user_id: Telegram user ID
        tier: Subscription tier (pro)
        payment_id: Payment record ID
        promo_code: Promo code used (if any)
        duration_days: Subscription duration in days
    
    Returns:
        True if activation successful
    """
    try:
        with get_db() as db:
            # Create/upgrade subscription
            subscription = create_pro_subscription(
                db,
                user_id=user_id,
                duration_days=duration_days,
                payment_id=payment_id
            )
            
            # Record promo code usage if applicable
            if promo_code:
                promo = get_promo_code(db, promo_code)
                if promo:
                    # Calculate actual discount amount
                    from services.promo_service import calculate_discounted_price
                    original_price = 24.99
                    final_price = calculate_discounted_price(original_price, promo.discount_percent or 0)
                    discount_amount = original_price - final_price
                    
                    record_promo_usage(
                        db,
                        promo_code=promo_code,
                        user_id=user_id,
                        payment_id=payment_id,
                        discount_applied=discount_amount
                    )
                    logger.info(f"Recorded promo code usage for user {user_id}: {promo_code}")
            
            logger.info(
                f"Subscription activated for user {user_id}: "
                f"tier={tier}, expires={subscription.expiry_date}"
            )
            return True
            
    except Exception as e:
        logger.error(f"Failed to activate subscription for user {user_id}: {e}", exc_info=True)
        return False


async def send_subscription_activated_notification(bot, user_id: int) -> None:
    """
    Send notification to user that subscription is activated.
    
    Args:
        bot: Telegram bot instance
        user_id: Telegram user ID
    """
    try:
        message = (
            "🎉 <b>Подписка активирована!</b>\n\n"
            "✅ Pro подписка успешно оплачена\n"
            "⏰ Действует: 30 дней\n\n"
            "Теперь вы можете:\n"
            "• Безлимитные сессии с AI\n"
            "• Неограниченное время разговора\n"
            "• Полный доступ ко всем функциям\n\n"
            "Запустить Sfera AI: /start"
        )
        
        await bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="HTML"
        )
        
        logger.info(f"Sent activation notification to user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to send activation notification to user {user_id}: {e}")
