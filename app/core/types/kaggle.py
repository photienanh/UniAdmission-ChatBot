import sys
if sys.version_info.minor >= 12:
    from typing import TypedDict, NotRequired
else:
    from typing_extensions import TypedDict, NotRequired
from .model import ModelInfo, ModelPreOutput, ModelOutput, GenerationParams, AnswerState
from .role import ChatMessageRole

class ChatMessage(TypedDict):
    role: ChatMessageRole
    answer_state: NotRequired[AnswerState]
    user_intent: NotRequired[str]
    summary: str
    entities: list[str]
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
    
class KaggleStoreChatData(TypedDict):
    forward_kwargs: dict
    model_output: ModelOutput