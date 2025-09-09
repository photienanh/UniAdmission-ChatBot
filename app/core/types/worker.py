import sys
if sys.version_info.minor >= 12:
    from typing import TypedDict
else:
    from typing_extensions import TypedDict
from .model import ModelInfo, ModelPreOutput, ModelOutput, GenerationParams
from .role import ChatMessageRole

class ChatMessage(TypedDict):
    role: ChatMessageRole
    text: str
    
class WorkerServerInfo(TypedDict):
    name: str
    domain: str
    models: list[ModelInfo]   
    
class WorkerPreInferenceResponse(TypedDict):
    pre_output: ModelPreOutput
    info: WorkerServerInfo
    
class WorkerChatRequest(TypedDict):
    text: str
    params: GenerationParams
    history: list[ChatMessage]
    forward_kwargs: dict
    
class WorkerStoreChatData(TypedDict):
    forward_kwargs: dict
    model_output: ModelOutput