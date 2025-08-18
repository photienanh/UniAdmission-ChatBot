from typing import TypedDict, Literal, Optional, NotRequired
from .rag import WebSource, RagSource, SearchEngineType

ModelSource = Literal["server", "kaggle"]

class ModelInfo(TypedDict):
    name: str
    id: str
    streaming: bool
    source: ModelSource

class GenerationParams(TypedDict):
    engine_type: NotRequired[SearchEngineType]
    query_rewrite: NotRequired[bool]
    hyde: NotRequired[bool]
    domain_restric: NotRequired[bool]
    k_docs: NotRequired[int]
    k_pages: NotRequired[int]
    max_tokens: NotRequired[int]
    temperature: NotRequired[float]
    top_p: NotRequired[float]
    top_k: NotRequired[int]

class ModelPreOutput(TypedDict):
    stream_id: str
    model_id: str
    generation_params: GenerationParams
    web_sources: list[WebSource]
    rag_sources: list[RagSource]
    extra_data: dict