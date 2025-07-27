from typing import cast, Literal
from .models import DBSession, Column, ChatMessage, ChatSession, DateTime
from fastapi import HTTPException


def create_chat_session(user_id: str, title: str | None = None):
    chat_session = ChatSession()
    chat_session.user_id = user_id
    if title:
        chat_session.title = title
    DBSession.session.add(chat_session)
    DBSession.session.flush()
    return chat_session

def get_chat_session(session_id: str) -> ChatSession | None:
    session = DBSession.session.query(ChatSession).filter_by(id=session_id).first()
    if session:
        return session

def create_message(session_id: str, sender: Literal["user", "bot"], content: str) ->  ChatMessage:
    """
    Create new message, no commit
    """
    chat_message = ChatMessage()
    chat_message.session_id = session_id
    chat_message.content = content
    chat_message.sender = sender
    DBSession.session.add(chat_message)
    return chat_message

def get_user_sessions(user_id: str, is_archived: bool) -> list[ChatSession]:
    sessions = DBSession.session.query(ChatSession).filter_by(
        user_id=user_id,
        is_archived=is_archived
    ).order_by(cast(Column[DateTime], ChatSession.updated_at).desc()).all()
    return sessions

def get_session_messages(session_id: str, user_id: str) -> tuple[ChatSession, list[ChatMessage]]:
    chat_session = DBSession.session.query(ChatSession).filter_by(id=session_id).first()
    if chat_session and chat_session.user_id == user_id:
        return (chat_session, list(chat_session.messages))
    else:
        raise HTTPException(
            status_code=404,
            detail="Session không tồn tại"
        )
        