from typing import Literal, Optional, NotRequired
from typing_extensions import TypedDict

# All from core.types

SearchEngineType = Literal["google", "brave"]
ChatMessageRole = Literal["user", "bot"] # System instruction should stored per user message

class RagSource(TypedDict):
    url: str
    title: str
    text: str
class WebSource(TypedDict):
    url: str
    title: str
    description: str
    text: str

class ModelInfo(TypedDict):
    name: str
    id: str

class GenerationParams(TypedDict):
    engine_type: NotRequired[SearchEngineType]
    query_rewrite: NotRequired[bool]
    hyde: NotRequired[bool]
    domain_restrict: NotRequired[bool]
    k_docs: NotRequired[int]
    k_pages: NotRequired[int]
    max_tokens: NotRequired[int]
    temperature: NotRequired[float]
    top_p: NotRequired[float]
    top_k: NotRequired[int]
    max_history: NotRequired[int]

class ModelPreOutput(TypedDict):
    model_id: str
    generation_params: GenerationParams
    web_sources: list[WebSource]
    rag_sources: list[RagSource]
    extra_data: dict
    result_url: str
    
class ModelOutput(ModelPreOutput):
    text: str
    
class ChatMessage(TypedDict):
    role: ChatMessageRole
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