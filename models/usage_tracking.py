"""Usage tracking model for subscription limits."""

from sqlalchemy import Column, Integer, BigInteger, Float, Date, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class UsageTracking(Base):
    __tablename__ = "usage_tracking"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False)

    # Daily reset at midnight
    tracking_date = Column(Date, default=func.current_date(), nullable=False)

    # Counters
    sessions_today = Column(Integer, default=0)
    minutes_today = Column(Float, default=0.0)
    kb_queries_today = Column(Integer, default=0)
    web_searches_today = Column(Integer, default=0)

    # Session details
    last_session_start = Column(DateTime, nullable=True)
    last_session_end = Column(DateTime, nullable=True)

    # Relationship
    user = relationship("User", back_populates="usage_records")

    __table_args__ = (
        Index("ix_usage_user_date", "user_id", "tracking_date", unique=True),
    )
