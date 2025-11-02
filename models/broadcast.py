from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from .base import Base


class ScheduledBroadcast(Base):
    __tablename__ = "scheduled_broadcasts"
    
    id = Column(Integer, primary_key=True, index=True)
    message_content = Column(Text, nullable=False)  # JSON-строка с содержимым сообщения
    scheduled_datetime = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    admin_id = Column(Integer, nullable=False)  # ID администратора, создавшего рассылку