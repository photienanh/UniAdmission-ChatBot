from typing import Optional, Literal, Any, TypedDict
from datetime import datetime
from .model import SourceInfo, WebSearchParam

class ChatRequest(TypedDict):
    message: str
    model_id: str
    session_id: Optional[str]
    web_search: Optional[WebSearchParam]

class SessionResponse(TypedDict):
    id: str 
    title: str 
    created_at: datetime
    updated_at: datetime 
    message_count: int
    preview: str 

class MessageResponse(TypedDict):
    id: str
    session_id: str
    role: Literal["user", "bot"]
    message: str
    timestamp: datetime
    message_type: Literal['text', 'image', 'file']
    rag_sources: list[SourceInfo]
    search_sources: list[SourceInfo]
    model_id: Optional[str]
    extra_data: Optional[dict]

class SessionMessagesResponse(TypedDict):
    session: SessionResponse
    messages: list[MessageResponse]
    
class CreateChatSessionData(TypedDict):
    title: str