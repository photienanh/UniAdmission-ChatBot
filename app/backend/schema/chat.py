from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal, Any
from datetime import datetime

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    model_type: str = Field(...)
    session_id: Optional[str] = Field(None)
    use_web_search: bool = Field(True)
    
class SourceInfo(BaseModel):
    url: str = Field(...)
    title: str = Field(...)
    content: str = Field(...)
    
class ChatResponse(BaseModel):
    response: str = Field(...)
    session_id: str = Field(...)
    context: str = Field(...)
    message_id: str = Field(...)
    sources: list[SourceInfo] = Field(...)
    search_sources: list[SourceInfo] = Field(...)
    
class SessionResponse(BaseModel):
    id: str = Field(...)
    title: str = Field(...)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    message_count: int = Field(...)
    preview: str = Field(...)

class MessageResponse(BaseModel):
    id: str = Field(...)
    sender: Literal['bot', 'uesr'] = Field(...)
    content: str = Field(...)
    timestamp: str = Field(...)
    message_type: Literal['text', 'image', 'file'] = Field('text')
    extra_data: Optional[Any] = Field(...)

class SessionMessagesResponse(BaseModel):
    session: SessionResponse
    messages: list[MessageResponse]
    
class CreateChatSessionRequest(BaseModel):
    title: str = Field(...)