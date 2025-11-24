from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession
from .base import Base, generate_id, datetime_now, cast
from datetime import datetime
from typing import Optional

class MessageRating(Base): #type:ignore
    __tablename__ = "message_rating"
    
    id = cast(str, Column(String(36), primary_key=True, default=generate_id))
    message_id = cast(str, Column(String(36), ForeignKey("chat_message.id"), nullable=False, unique=True))
    user_id = cast(str, Column(String(36), ForeignKey("user.id"), nullable=False))
    rating = cast(int, Column(Integer, nullable=False))  # 1-5 stars
    timestamp = cast(datetime, Column(DateTime, default=datetime_now))
    
    def to_dict(self):
        return {
            "id": self.id,
            "message_id": self.message_id,
            "user_id": self.user_id,
            "rating": self.rating,
            "timestamp": self.timestamp.isoformat()
        }

