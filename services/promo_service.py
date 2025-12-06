"""Promo code validation service."""

from datetime import datetime
from typing import Tuple
import logging

from db_session import get_db
from models.subscription_crud import (
    get_promo_code,
    has_user_used_promo,
)

logger = logging.getLogger(__name__)


async def validate_promo_code(
    code: str,
    user_id: int,
    tier: str
) -> Tuple[bool, float, str]:
    """
    Validate promo code for user and tier.
    
    Args:
        code: Promo code string
        user_id: Telegram user ID
        tier: Subscription tier (pro)
    
    Returns:
        (valid: bool, discount_percent: float, message: str)
    """
    code = code.strip().upper()
    
    with get_db() as db:
        promo = get_promo_code(db, code)
        
        if not promo:
            logger.info(f"Promo code '{code}' not found")
            return False, 0, "❌ Промокод не найден"
        
        if not promo.is_active:
            logger.info(f"Promo code '{code}' is inactive")
            return False, 0, "❌ Промокод деактивирован"
        
        # Check expiry
        if promo.valid_until and promo.valid_until < datetime.now():
            logger.info(f"Promo code '{code}' expired at {promo.valid_until}")
            return False, 0, "❌ Срок действия промокода истек"
        
        # Check usage limit
        if promo.max_uses and promo.current_uses >= promo.max_uses:
            logger.info(f"Promo code '{code}' usage limit reached ({promo.current_uses}/{promo.max_uses})")
            return False, 0, "❌ Достигнут лимит использования промокода"
        
        # Check tier restriction
        if promo.tier_restriction and promo.tier_restriction != tier:
            logger.info(f"Promo code '{code}' not valid for tier '{tier}'")
            return False, 0, f"❌ Промокод действителен только для {promo.tier_restriction}"
        
        # Check if user already used this promo
        if has_user_used_promo(db, user_id, promo.id):
            logger.info(f"User {user_id} already used promo code '{code}'")
            return False, 0, "❌ Вы уже использовали этот промокод"
        
        # Calculate discount
        discount = promo.discount_percent or 0
        
        logger.info(f"Promo code '{code}' valid for user {user_id}: {discount}% discount")
        return True, discount, "✅ Промокод действителен"


def calculate_discounted_price(original_price: float, discount_percent: float) -> float:
    """
    Calculate final price with discount applied.
    
    Args:
        original_price: Original price in USD
        discount_percent: Discount percentage (e.g., 20 = 20% off)
    
    Returns:
        Final price after discount
    """
    if discount_percent <= 0:
        return original_price
    
    discount_amount = original_price * (discount_percent / 100)
    final_price = original_price - discount_amount
    
    return round(final_price, 2)
