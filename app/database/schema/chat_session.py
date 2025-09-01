from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from config import CHAT_SESSION_TITLE_LENGTH
from .base import *
from .chat_message import ChatMessage

class ChatSession(Base): #type:ignore
    __tablename__ = "chat_session"
    
    id = cast(str, Column(String(36), primary_key=True, default=generate_id))
    user_id = cast(str, Column(String(36), ForeignKey("user.id"), nullable=False)) # ForeignKey to user.id
    title = cast(Optional[str], Column(String(CHAT_SESSION_TITLE_LENGTH)))
    created_at = cast(datetime, Column(DateTime, default=datetime_now))
    updated_at = cast(datetime, Column(DateTime, default=datetime_now, onupdate=datetime_now))
    messages = cast(list["ChatMessage"], relationship("ChatMessage", backref="session", lazy=True, cascade="all, delete-orphan")) # One-to-many relationship with ChatMessage

    def __preview_from_content(self, content: str):
        """Lấy preview cho session title"""
        preview = content[:CHAT_SESSION_TITLE_LENGTH]
        if len(preview) > CHAT_SESSION_TITLE_LENGTH:
            preview += "..."
        return preview
    
    async def _get_message_count(self, ss: AsyncSession):
        """Lấy số lượng message trong session"""
        result = await ss.execute(select(func.count(ChatMessage.id)).where(ChatMessage.session_id==self.id)) #type:ignore
        count = result.scalar_one()
        return count
    
    async def _get_first_message(self, ss: AsyncSession):
        """Lấy message đầu tiên trong session (theo timestamp)"""
        result = await ss.execute(select(ChatMessage).where(ChatMessage.session_id==self.id).order_by(ChatMessage.timestamp).limit(1))#type:ignore
        first_msg = result.scalar_one_or_none()
        return first_msg
    
    async def get_preview(self, ss: AsyncSession):
        """Lấy preview cho session title từ message đầu tiên"""
        first_msg = await self._get_first_message(ss)
        if first_msg:
            return self.__preview_from_content(first_msg.text)
        
    async def set_title_if_null(self, ss: AsyncSession):
        """Nếu title là None thì set title từ tin nhắn đầu tiên"""
        if not self.title:
            first_msg = await self._get_first_message(ss)
            if first_msg:
                self.title = self.__preview_from_content(first_msg.text)

    async def prepare_to_dict(self, ss: AsyncSession):
        """Chạy bên trong AsyncSession, thêm thuộc tính msg_count và preview vào object"""
        setattr(self, "msg_count", await self._get_message_count(ss))
        setattr(self, "preview", await self.get_preview(ss))

    def to_dict(self):
        """Chuyển thành dict, có thể gọi ngoài session context"""
        preview = str(getattr(self, "preview"))
        msg_count = int(getattr(self, "msg_count"))
        return {
            "id": self.id,
            "title": self.title or preview, # fallback cho DB cũ chưa có title
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": msg_count,
            "preview": preview
        }