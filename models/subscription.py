"""Subscription model for tiered access control."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger, Float, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum

from .base import Base


class TierEnum(str, Enum):
    FREE = "free"
    PRO = "pro"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), unique=True, nullable=False)

    # Tier management
    tier = Column(SQLEnum(TierEnum), default=TierEnum.FREE, nullable=False)
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)

    # Billing
    start_date = Column(DateTime, nullable=False, default=func.now())
    expiry_date = Column(DateTime, nullable=True)  # NULL = lifetime/free tier
    auto_renew = Column(Boolean, default=False)

    # Payment tracking
    payment_method = Column(String, nullable=True)  # "crypto", "manual"
    last_payment_date = Column(DateTime, nullable=True)
    last_payment_amount = Column(Float, nullable=True)

    # Relationships
    user = relationship("User", back_populates="subscription")
    payments = relationship("Payment", back_populates="subscription")

    __table_args__ = (
        Index("ix_subscription_tier_status", "tier", "status"),
        Index("ix_subscription_expiry", "expiry_date"),
    )

    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        from datetime import datetime
        
        if self.status != SubscriptionStatus.ACTIVE:
            return False
        
        if self.tier == TierEnum.FREE:
            return True
        
        if self.expiry_date and self.expiry_date < datetime.now():
            return False
        
        return True

    def get_tier(self) -> str:
        """Get current tier, accounting for expiry."""
        if not self.is_active() and self.tier != TierEnum.FREE:
            return TierEnum.FREE.value
        return self.tier.value
