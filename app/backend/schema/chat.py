from pydantic import BaseModel
import sys
if sys.version_info.minor >= 12:
    from typing import TypedDict
else:
    from typing_extensions import TypedDict
from typing import Optional
from datetime import datetime

from core.types import GenerationParams, ChatMessageRole, RagSource, WebSource

class ChatRequest(BaseModel):
    text: str
    model_id: str
    session_id: Optional[str]
<<<<<<< HEAD
    web_search: Optional[WebSearchParam]
    sampling_params: dict

class SessionResponse(TypedDict):
    id: str 
    title: str 
    created_at: datetime
    updated_at: datetime 
    message_count: int
    preview: str 

=======
    params: GenerationParams
    
class PreChatResponse(TypedDict):
    session_id: str
    role: ChatMessageRole
    rag_sources: list[RagSource]
    web_sources: list[WebSource]
    extra_data: dict
    result_url: str
    
>>>>>>> 36adcd4a3b9a4de7c67ba0935221121c9e22a799
class MessageResponse(TypedDict):
    id: str
    text: str
    model_id: Optional[str]
    session_id: str
    role: ChatMessageRole
    timestamp: datetime
    rag_sources: list[RagSource]
    web_sources: list[WebSource]
    generation_params: GenerationParams
    extra_data: dict
    
class SessionResponse(TypedDict):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    preview: str
    
class SessionMessagesResponse(TypedDict):
    session: SessionResponse
    messages: list[MessageResponse]