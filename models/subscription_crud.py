"""CRUD operations for subscription system."""

from datetime import datetime, timedelta, date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from .subscription import Subscription, TierEnum, SubscriptionStatus
from .usage_tracking import UsageTracking
from .payment import Payment, PaymentMethod, PaymentStatus
from .promo_code import PromoCode, PromoCodeUsage


# ==================== SUBSCRIPTION CRUD ====================

def get_user_subscription(db: Session, user_id: int) -> Optional[Subscription]:
    """Get user's active subscription."""
    return db.query(Subscription).filter(Subscription.user_id == user_id).first()


def create_free_subscription(db: Session, user_id: int) -> Subscription:
    """Create free tier subscription for new user."""
    subscription = Subscription(
        user_id=user_id,
        tier=TierEnum.FREE,
        status=SubscriptionStatus.ACTIVE,
        start_date=datetime.now(),
        expiry_date=None,  # Free never expires
        payment_method=None
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def create_pro_subscription(
    db: Session,
    user_id: int,
    duration_days: int = 30,
    payment_id: Optional[int] = None
) -> Subscription:
    """Create or update to Pro subscription."""
    subscription = get_user_subscription(db, user_id)
    
    if subscription:
        # Update existing
        subscription.tier = TierEnum.PRO
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.start_date = datetime.now()
        subscription.expiry_date = datetime.now() + timedelta(days=duration_days)
        subscription.payment_method = "crypto"
        subscription.last_payment_date = datetime.now()
    else:
        # Create new
        subscription = Subscription(
            user_id=user_id,
            tier=TierEnum.PRO,
            status=SubscriptionStatus.ACTIVE,
            start_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=duration_days),
            payment_method="crypto"
        )
        db.add(subscription)
    
    db.commit()
    db.refresh(subscription)
    return subscription


def cancel_subscription(db: Session, user_id: int) -> bool:
    """Cancel user's subscription (downgrade to free)."""
    subscription = get_user_subscription(db, user_id)
    if not subscription:
        return False
    
    subscription.tier = TierEnum.FREE
    subscription.status = SubscriptionStatus.CANCELLED
    subscription.expiry_date = None
    subscription.auto_renew = False
    
    db.commit()
    return True


def count_subscriptions_by_tier(db: Session) -> dict:
    """Get subscription counts by tier."""
    from sqlalchemy import case
    
    results = db.query(
        Subscription.tier,
        func.count(Subscription.id).label('count')
    ).filter(
        Subscription.status == SubscriptionStatus.ACTIVE
    ).group_by(Subscription.tier).all()
    
    return {tier: count for tier, count in results}


# ==================== USAGE TRACKING CRUD ====================

def get_today_usage(db: Session, user_id: int) -> Optional[UsageTracking]:
    """Get today's usage record for user."""
    today = date.today()
    return db.query(UsageTracking).filter(
        UsageTracking.user_id == user_id,
        UsageTracking.tracking_date == today
    ).first()


def get_or_create_today_usage(db: Session, user_id: int) -> UsageTracking:
    """Get or create today's usage record."""
    usage = get_today_usage(db, user_id)
    if not usage:
        usage = UsageTracking(
            user_id=user_id,
            tracking_date=date.today(),
            sessions_today=0,
            minutes_today=0.0,
            kb_queries_today=0,
            web_searches_today=0
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)
    return usage


def increment_session_count(db: Session, user_id: int) -> None:
    """Increment session counter for today."""
    usage = get_or_create_today_usage(db, user_id)
    usage.sessions_today += 1
    usage.last_session_start = datetime.now()
    db.commit()


def add_session_duration(db: Session, user_id: int, duration_minutes: float) -> None:
    """Add duration to today's usage."""
    usage = get_or_create_today_usage(db, user_id)
    usage.minutes_today += duration_minutes
    usage.last_session_end = datetime.now()
    db.commit()


# ==================== PAYMENT CRUD ====================

def create_payment(
    db: Session,
    user_id: int,
    amount: float,
    currency: str,
    method: PaymentMethod,
    tier: str,
    heleket_payment_id: Optional[str] = None,
    promo_code: Optional[str] = None
) -> Payment:
    """Create new payment record."""
    subscription = get_user_subscription(db, user_id)
    
    payment = Payment(
        user_id=user_id,
        amount=amount,
        currency=currency,
        method=method,
        heleket_payment_id=heleket_payment_id,
        status=PaymentStatus.PENDING,
        tier=tier,
        promo_code=promo_code,
        subscription_id=subscription.id if subscription else None
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def update_payment_status(
    db: Session,
    heleket_payment_id: str,
    status: PaymentStatus
) -> bool:
    """Update payment status."""
    payment = db.query(Payment).filter(
        Payment.heleket_payment_id == heleket_payment_id
    ).first()
    
    if not payment:
        return False
    
    payment.status = status
    if status == PaymentStatus.COMPLETED:
        payment.completed_at = datetime.now()
    
    db.commit()
    return True


# ==================== PROMO CODE CRUD ====================

def get_promo_code(db: Session, code: str) -> Optional[PromoCode]:
    """Get promo code by code."""
    return db.query(PromoCode).filter(
        PromoCode.code == code.upper()
    ).first()


def create_promo_code(
    db: Session,
    code: str,
    discount_percent: float,
    created_by: int,
    max_uses: Optional[int] = None,
    valid_days: Optional[int] = None
) -> PromoCode:
    """Create new promo code."""
    promo = PromoCode(
        code=code.upper(),
        discount_percent=discount_percent,
        created_by=created_by,
        max_uses=max_uses,
        valid_until=datetime.now() + timedelta(days=valid_days) if valid_days else None
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return promo


def get_all_promo_codes(db: Session) -> list[PromoCode]:
    """Get all promo codes."""
    return db.query(PromoCode).order_by(PromoCode.created_at.desc()).all()


def deactivate_promo_code(db: Session, code: str) -> bool:
    """Deactivate promo code."""
    promo = get_promo_code(db, code)
    if not promo:
        return False
    
    promo.is_active = False
    db.commit()
    return True


def has_user_used_promo(db: Session, user_id: int, promo_code_id: int) -> bool:
    """Check if user already used this promo code."""
    usage = db.query(PromoCodeUsage).filter(
        PromoCodeUsage.user_id == user_id,
        PromoCodeUsage.promo_code_id == promo_code_id
    ).first()
    return usage is not None


def record_promo_usage(
    db: Session,
    promo_code: str,
    user_id: int,
    payment_id: int,
    discount_applied: float
) -> None:
    """Record promo code usage."""
    promo = get_promo_code(db, promo_code)
    if not promo:
        return
    
    usage = PromoCodeUsage(
        promo_code_id=promo.id,
        user_id=user_id,
        payment_id=payment_id,
        discount_applied=discount_applied
    )
    db.add(usage)
    
    # Increment usage counter
    promo.current_uses += 1
    
    db.commit()
