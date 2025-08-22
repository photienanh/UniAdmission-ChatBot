from typing import Literal, Optional, NotRequired
from typing_extensions import TypedDict

# All from core.types

ModelSource = Literal["server", "kaggle"]
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

class ModelInfo(TypedDict):
    name: str
    id: str
    streaming: bool
    source: ModelSource
    
class ModelPreOutput(TypedDict):
    stream_id: str
    model_id: str
    generation_params: GenerationParams
    web_sources: list[WebSource]
    rag_sources: list[RagSource]
    extra_data: dict
    
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
    text: str
    model_id: str
    stream_id: str
    params: GenerationParams
    