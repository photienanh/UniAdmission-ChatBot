from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from .base import Base, generate_id, datetime_now, cast
from datetime import datetime

class MessagePreference(Base): #type:ignore
    """
    A/B Preference: User chooses which response is better
    Triggered when rating <= 3 stars
    """
    __tablename__ = "message_preference"
    
    id = cast(str, Column(String(36), primary_key=True, default=generate_id))
    user_id = cast(str, Column(String(36), ForeignKey("user.id"), nullable=False))
    
    query_text = cast(str, Column(Text, nullable=False))
    
    # Response A (original, got low rating)
    original_message_id = cast(str, Column(String(36), ForeignKey("chat_message.id"), nullable=False))
    
    # Response B (regenerated)
    regenerated_message_id = cast(str, Column(String(36), ForeignKey("chat_message.id"), nullable=False))
    
    # Which one user chose
    preferred_message_id = cast(str, Column(String(36), ForeignKey("chat_message.id"), nullable=False))
    
    # Metadata
    timestamp = cast(datetime, Column(DateTime, default=datetime_now))
    trigger_type = cast(str, Column(String(20), default="low_rating"))  # low_rating, manual, random
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "query_text": self.query_text,
            "original_message_id": self.original_message_id,
            "regenerated_message_id": self.regenerated_message_id,
            "preferred_message_id": self.preferred_message_id,
            "timestamp": self.timestamp.isoformat(),
            "trigger_type": self.trigger_type
        }

