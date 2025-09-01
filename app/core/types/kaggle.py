import sys
if sys.version_info.minor >= 12:
    from typing import TypedDict, NotRequired
else:
    from typing_extensions import TypedDict, NotRequired
from .model import ModelInfo, ModelPreOutput, GenerationParams
from .role import ChatMessageRole

class ChatMessage(TypedDict):
    role: ChatMessageRole
    content: str

class ModelStatus(ModelInfo):
    active: bool
    scheduled: bool
    active_count: int
    scheduled_count: int
    
class KaggleServerInfo(TypedDict):
    name: str
    domain: str
    models: list[ModelStatus]   
    
class KagglePreInferenceResponse(TypedDict):
    pre_output: ModelPreOutput
    info: KaggleServerInfo
    
class KaggleRequest(TypedDict):
    question: str
    model_id: str
    stream_id: str
    params: GenerationParams
    history: list[ChatMessage]
    vector_sources: NotRequired[list]  # Sources from app/ vector search
    web_search_keywords: NotRequired[list[str]]  # Keywords for kaggle web search