from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger, Index
from sqlalchemy.sql import func

from .base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # Вот здесь было изменение: Integer -> BigInteger
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)

    is_approved = Column(Boolean, default=False)
    approval_date = Column(DateTime, nullable=True)

    is_banned = Column(Boolean, default=False)
    awaiting_verification = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_user_username_lower", func.lower(username), unique=False),
        Index("ix_user_last_seen_active", "last_seen", "is_approved"),
        Index("ix_user_verification_status", "awaiting_verification", "is_approved"),
        Index("ix_user_banned_status", "is_banned"),
    )
