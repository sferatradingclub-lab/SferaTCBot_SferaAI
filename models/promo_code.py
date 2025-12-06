"""Promo code models for discount management."""

from sqlalchemy import Column, Integer, String, BigInteger, Float, DateTime, Boolean, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum

from .base import Base


class TierRestriction(str, Enum):
    FREE = "free"
    PRO = "pro"


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)

    # Discount
    discount_percent = Column(Float, nullable=True)  # e.g., 20 = 20% off
    discount_amount = Column(Float, nullable=True)   # or fixed amount discount

    # Validity
    valid_from = Column(DateTime, default=func.now(), nullable=False)
    valid_until = Column(DateTime, nullable=True)  # NULL = no expiry
    max_uses = Column(Integer, nullable=True)  # NULL = unlimited
    current_uses = Column(Integer, default=0, nullable=False)

    # Restrictions
    tier_restriction = Column(SQLEnum(TierRestriction), nullable=True)  # NULL = any tier

    # Metadata
    created_by = Column(BigInteger, nullable=False)  # Admin user_id
    created_at = Column(DateTime, default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    usages = relationship("PromoCodeUsage", back_populates="promo_code")

    __table_args__ = (
        Index("ix_promo_active_valid", "is_active", "valid_until"),
    )


class PromoCodeUsage(Base):
    __tablename__ = "promo_code_usage"

    id = Column(Integer, primary_key=True, index=True)
    promo_code_id = Column(Integer, ForeignKey("promo_codes.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    
    used_at = Column(DateTime, default=func.now(), nullable=False)
    discount_applied = Column(Float, nullable=False)  # Actual discount amount in $

    # Relationships
    promo_code = relationship("PromoCode", back_populates="usages")
    user = relationship("User", back_populates="promo_usage")
    payment = relationship("Payment", back_populates="promo_usage")

    __table_args__ = (
        Index("ix_promo_usage_user", "promo_code_id", "user_id"),
    )
