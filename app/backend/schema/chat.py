from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal, Any
from datetime import datetime

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    model_type: str = Field(...)
    session_id: Optional[str] = Field(None)
    use_web_search: bool = Field(True)
    
class SourceInfo(BaseModel):
    url: str
    title: str
    content: Optional[str] 
    
class ChatResponse(BaseModel):
    response: str 
    session_id: str
    message_id: str 
    context: Optional[str] 
    sources: list[SourceInfo] 
    search_sources: list[SourceInfo]
    
    
    
class SessionResponse(BaseModel):
    id: str 
    title: str 
    created_at: datetime
    updated_at: datetime 
    message_count: int
    preview: str 

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