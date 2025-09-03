import sys
if sys.version_info.minor >= 12:
    from typing import TypedDict, Optional
else:
    from typing_extensions import TypedDict, Optional
from .model import ModelInfo, ModelPreOutput, ModelOutput, GenerationParams, AnswerState
from .role import ChatMessageRole

class ChatMessage(TypedDict):
    role: ChatMessageRole
    answer_state: Optional[AnswerState]
    user_intent: Optional[str]
    summary: str
    keywords: list[str]
    text: str

class ModelStatus(ModelInfo):
    active: bool
    scheduled: bool
    active_count: int
    scheduled_count: int
    
class WorkerServerInfo(TypedDict):
    name: str
    domain: str
    models: list[ModelStatus]   
    
class WorkerPreInferenceResponse(TypedDict):
    pre_output: ModelPreOutput
    info: WorkerServerInfo
    
class WorkerChatRequest(TypedDict):
    text: str
    model_id: str
    stream_id: str
    params: GenerationParams
    history: list[ChatMessage]
    forward_kwargs: dict
    
class WorkerStoreChatData(TypedDict):
    forward_kwargs: dict
    model_output: ModelOutput