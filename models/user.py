from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)

    is_banned = Column(Boolean, default=False)

    # Relationships - NEW
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    usage_records = relationship("UsageTracking", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    promo_usage = relationship("PromoCodeUsage", back_populates="user")

    __table_args__ = (
        Index("ix_user_username_lower", func.lower(username), unique=False),
        Index("ix_user_last_seen", "last_seen"),
        Index("ix_user_banned_status", "is_banned"),
    )

    @property
    def current_tier(self) -> str:
        """Get current subscription tier."""
        if not self.subscription or not self.subscription.is_active():
            return "free"
        return self.subscription.get_tier()

