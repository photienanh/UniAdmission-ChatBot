from typing import cast
from sqlalchemy import Column, DateTime, select
from sqlalchemy.orm import selectinload
import traceback
import datetime

from database.manager import session                    # context manager để mở session DB
from database.schema import ChatSession, ChatMessage    # ORM models cho bảng ChatSession & ChatMessage
from core.types import ChatMessageRole, WebSource, RagSource, GenerationParams

async def get_chat_session(session_id: str) -> ChatSession | None:
    """Lấy ChatSession theo session_id"""
    async with session() as ss:
        chat_session = (await ss.execute(
            select(ChatSession).filter_by(id=session_id)
        )).scalar()
        if chat_session:
            return chat_session

async def get_user_sessions(user_id: str, prepare_to_dict: bool = True) -> list[ChatSession]:
    """Lấy tất cả ChatSession của một User"""
    async with session() as ss:
        # Lấy danh sách session theo user_id, sort theo updated_at (mới nhất trước)
        chat_sessions = (await ss.execute(
            select(ChatSession).filter_by(user_id=user_id)
            .order_by(cast(Column[DateTime], ChatSession.updated_at).desc())
        )).scalars().all()

        result: list[ChatSession] = []
        if prepare_to_dict:
            # Gọi hàm prepare_to_dict để chuẩn bị dữ liệu serialize
            for chat_session in chat_sessions:
                await chat_session.prepare_to_dict(ss)
                result.append(chat_session)
        return result

async def __get_session(session_id: str, user_id: str) -> ChatSession | None:
    """(Private) Lấy ChatSession theo session_id, 
       chỉ trả về nếu session thuộc về đúng user_id"""
    async with session() as ss:
        chat_session = (await ss.execute(
            select(ChatSession).filter_by(id=session_id)
        )).scalar()
        if chat_session and chat_session.user_id == user_id: # Kiểm tra quyền sở hữu
            return chat_session
        else:
            return None

async def get_session_with_messages(session_id: str) -> ChatSession | None:
    """Lấy ChatSession cùng toàn bộ ChatMessage của nó"""
    async with session() as ss:
        result = await ss.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))   # eager load messages
            .where(ChatSession.id == session_id)
        )
        chat_session = result.scalar()
        if chat_session:
            await chat_session.prepare_to_dict(ss)         # chuẩn hóa dữ liệu
            return chat_session

async def get_message(message_id: str) -> ChatMessage | None:
    """Lấy một ChatMessage theo id"""
    async with session() as ss:
        message = (await ss.execute(
            select(ChatMessage).filter_by(id=message_id)
        )).scalar()
        return message

def __create_message(
    session_id: str,
    role: ChatMessageRole,
    text: str,
    model_id: str,
    web_sources: list[WebSource],
    rag_sources: list[RagSource],
    params: GenerationParams,
    timestamp: datetime.datetime,
    extra_data: dict = {}
) -> ChatMessage:
    """
    Hàm helper để tạo một ChatMessage mới
    """
    msg = ChatMessage()
    msg.session_id = session_id
    msg.text = text
    msg.role = role
    
    msg.model_id = model_id
    msg.rag_sources = rag_sources
    msg.web_sources = web_sources
    msg.generation_params = params
    msg.timestamp = timestamp
    
    msg.extra_data = extra_data
    return msg

async def create_chat_session(user_id: str) -> str | None:
    """Tạo mới một ChatSession cho user"""
    async with session() as ss:        
        chat_session = ChatSession()
        chat_session.user_id = user_id
        try:
            ss.add(chat_session)
            await ss.flush()              # flush để có id ngay
            ss_id = chat_session.id
            await ss.commit()             # commit vào DB
            return ss_id
        except:
            await ss.rollback()
            traceback.print_exc()

async def add_conversation(
    user_id: str,
    session_id: str,
    user_text: str,
    bot_text: str,
    model_id: str,
    web_sources: list[WebSource],
    rag_sources: list[RagSource],
    params: GenerationParams,
    user_timestamp: datetime.datetime,
    bot_timestamp: datetime.datetime,
    user_extra_data: dict = {},
    bot_extra_data: dict = {},
    **kwargs
):
    """Thêm một cặp tin nhắn (user → bot) vào DB
       (không check quyền sở hữu session ở đây)"""
    async with session() as ss:
        # Tạo tin nhắn của user
        user_msg = __create_message(
            session_id=session_id,
            role="user",
            text=user_text,
            model_id=model_id,
            web_sources=[],   # user thường không có nguồn tham khảo
            rag_sources=[],
            params=params,
            timestamp=user_timestamp,
            extra_data=user_extra_data
        )
        # Tạo tin nhắn của bot
        bot_msg = __create_message(
            session_id=session_id,  
            role="bot",
            text=bot_text,
            model_id=model_id,
            web_sources=web_sources,
            rag_sources=rag_sources,
            params=params,
            timestamp=bot_timestamp,
            extra_data=bot_extra_data
        )
        ss.add(user_msg)
        ss.add(bot_msg)
        try:
            await ss.flush()                # flush để lấy id ngay
            user_msg_id = user_msg.id
            bot_msg_id = bot_msg.id

            # Check session có thuộc user hay không
            chat_session = await __get_session(session_id, user_id)
            if chat_session is None:
                raise Exception(f"Session not found {session_id}")

            # Nếu session chưa có title → đặt title từ tin nhắn đầu tiên
            await chat_session.set_title_if_null(ss)

            await ss.commit()
            return user_msg_id, bot_msg_id
        except:
            await ss.rollback()
            traceback.print_exc()
            return None, None

async def delete_chat_session(chat_session: ChatSession) -> bool:
    """
    Xóa một ChatSession (cùng với toàn bộ ChatMessage cascade).
    Trả về True nếu thành công, False nếu lỗi.
    """
    async with session() as ss:
        try:
            await ss.delete(chat_session)
            await ss.commit()
            return True
        except Exception:
            await ss.rollback()
            traceback.print_exc()
            return False