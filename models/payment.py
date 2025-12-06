"""Payment model for tracking transactions."""

from sqlalchemy import Column, Integer, String, BigInteger, Float, DateTime, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum

from .base import Base


class PaymentMethod(str, Enum):
    CRYPTO = "crypto"
    MANUAL = "manual"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)

    # Amount
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USDT", nullable=False)
    method = Column(SQLEnum(PaymentMethod), nullable=False)

    # Heleket specific
    heleket_payment_id = Column(String, unique=True, nullable=True, index=True)
    heleket_order_id = Column(String, unique=True, nullable=True)
    crypto_address = Column(String, nullable=True)
   
    # Status
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Связь с подпиской
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    tier = Column(String, nullable=True)  # tier at time of payment
    promo_code = Column(String, nullable=True)  # promo code used

    # Relationships
    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")
    promo_usage = relationship("PromoCodeUsage", back_populates="payment", uselist=False)

    __table_args__ = (
        Index("ix_payment_status_created", "status", "created_at"),
        Index("ix_payment_user_status", "user_id", "status"),
    )
