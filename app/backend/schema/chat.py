from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal, Any
from datetime import datetime

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    model_type: str
    session_id: Optional[str] = Field(None)
    use_web_search: bool = Field(True)
    search_results_count: int = Field(3, ge=1, le=4)  # Từ 1-4 trang
    priority_domains: bool = Field(True)  # Ưu tiên domain chính thức
    
class SourceInfo(BaseModel):
    url: str
    title: str
    description: str
    content: str
    
class ChatResponse(BaseModel):
    response: str
    session_id: str
    message_id: str
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
    id: str
    sender: Literal['bot', 'uesr']
    content: str
    timestamp: str
    message_type: Literal['text', 'image', 'file'] = Field('text')
    extra_data: Optional[Any]

class SessionMessagesResponse(BaseModel):
    session: SessionResponse
    messages: list[MessageResponse]
    
class CreateChatSessionRequest(BaseModel):
    title: str