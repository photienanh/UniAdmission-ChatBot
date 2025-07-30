
from sqlalchemy import (
    create_engine, Engine, Column,  ForeignKey, PrimaryKeyConstraint, 
    Integer, String, Boolean, Float, DateTime, Text, JSON
)
from sqlalchemy.orm import declarative_base, DeclarativeBase, Session, sessionmaker, relationship
from typing import cast, Optional, Any, Iterable
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse
import uuid
import os
from datetime import datetime, timezone
    
Base: DeclarativeBase = declarative_base()

class User(Base): #type:ignore
    __tablename__ = "users"
    
    id = cast(str, Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4())))
    username = cast(str, Column(String(80), unique=True, nullable=False))
    email = cast(str, Column(String(120), unique=True, nullable=False))
    password_hash = cast(str, Column(String(120), nullable=False))
    full_name = cast(Optional[str], Column(String(100), nullable=True))
    created_at = cast(datetime, Column(DateTime, default=datetime.now(timezone.utc)))
    last_login = cast(Optional[datetime], Column(DateTime, nullable=True))
    is_active = cast(bool, Column(Boolean, default=True))
    
    sessions = relationship("ChatSession", backref="user", lazy=True,  cascade="all, delete-orphan")
    
    def set_password(self, password: str):
        """Mã hóa và lưu password"""
        self.password_hash = generate_password_hash(password)
    def check_password(self, password: str):
        """Kiểm tra password"""
        return check_password_hash(cast(str, self.password_hash), password)
    
    def get_id(self):
        return str(self.id)
    
    def to_dict(self):
        """Chuyển đổi thành dictionary"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_authenticated": True
        }
    
class ChatSession(Base): #type:ignore
    __tablename__ = "chat_sessions"
    
    id = cast(str, Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4())))
    user_id = cast(str, Column(String(36), ForeignKey("users.id"), nullable=False))
    title = cast(Optional[str], Column(String(200), nullable=True))
    created_at = cast(datetime, Column(DateTime, default=datetime.now(timezone.utc)))
    updated_at = cast(datetime, Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc)))
    is_archived = cast(bool, Column(Boolean, default=False))
    
    # Relationship với ChatMessage
    messages = relationship("ChatMessage", backref="session", lazy=True, cascade="all, delete-orphan")
    
    def get_preview(self):
        """Lấy tin nhắn đầu tiên để làm preview"""
        first_message = DBSession.session.query(ChatMessage).filter_by(session_id=self.id, sender='user').first()
        if first_message:
            content = cast(str, first_message.content)
            return content[:50] + "..." if len(content) > 50 else content
        return "Cuộc trò chuyện mới"
    def auto_set_title(self):
        if not self.title:
            first_message = DBSession.session.query(ChatMessage).filter_by(session_id=self.id, sender='user').first()
            if first_message:
                content = first_message.content
                self.title = content[:50] + "..." if len(content) > 50 else content    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title or self.get_preview(),
            "created_at": cast(datetime, self.created_at).isoformat(),
            "updated_at": cast(datetime, self.updated_at).isoformat(),
            "message_count": len(list(self.messages)),
            "preview": self.get_preview()
        }
    
class ChatMessage(Base): #type:ignore
    __tablename__ = "chat_messages"
    
    id = cast(str, Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4())))
    session_id = cast(str, Column(String(36), ForeignKey("chat_sessions.id"), nullable=False))
    sender = cast(str, Column(String(10), nullable=False)) # 'user' hoặc 'bot' ? 'system' ?
    content = cast(str, Column(Text, nullable=False))
    timestamp = cast(str, Column(DateTime, default=datetime.now(timezone.utc)))
    message_type = cast(str, Column(String(20), default="text")) # 'text', 'image', 'file'
    extra_data = cast(Any, Column(JSON)) # Lưu thêm thông tin như thời gian phản hồi, tokens sử dụng, etc.

    context = cast(Optional[str], Column(Text, nullable=True))
    sources = cast(list, Column(JSON, nullable=True))
    search_sources = cast(list, Column(JSON, nullable=True))

    def to_dict(self):
        return {
            "id": self.id,
            "sender": self.sender,
            "content": self.content,
            "timestamp": cast(datetime, self.timestamp).isoformat(),
            "message_type": self.message_type,
            "extra_data": self.extra_data,
            "sources": self.sources,
            "search_sources": self.search_sources
        }

class DBSession:
    engine: Engine
    session: Session
    def __init__(self) -> None:
        raise NotImplementedError(f"Static class does not support instance")
    @classmethod
    def setup(cls, uri: str = "sqlite:///instance/chatbot_x.db", echo: bool = False):
        folder_path = os.path.dirname(urlparse(uri).path.lstrip("/"))
        os.makedirs(folder_path, exist_ok=True)
        DBSession.engine = create_engine(uri, echo=echo)
        Base.metadata.create_all(DBSession.engine)
        DBSession.session = sessionmaker(bind=DBSession.engine)()
    @classmethod
    def commit(cls):
        DBSession.session.commit()
    @classmethod
    def rollback(cls):
        DBSession.session.rollback()
    @classmethod
    def close(cls):
        DBSession.session.close()
        DBSession.engine.dispose()