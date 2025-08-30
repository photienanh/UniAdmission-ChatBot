import sys
if sys.version_info.minor >= 12:
    from typing import TypedDict
else:
    from typing_extensions import TypedDict
from typing import Literal, Optional, NotRequired
from .rag import WebSource, RagSource, SearchEngineType

ModelSource = Literal["server", "kaggle"]
AnswerState = Literal["need_clarification", "successfully", "partially", "relevant", "not_found", "other"]

class ModelInfo(TypedDict):
    name: str
    id: str
    streaming: bool
    source: ModelSource

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
    stream_id: str
    model_id: str
    generation_params: GenerationParams
    web_sources: list[WebSource]
    rag_sources: list[RagSource]
    extra_data: dict
    user_summary: str
    user_intent: str
    user_keywords: list[str]
    result_url: str

    
class ModelOutput(ModelPreOutput):
    answer_state: AnswerState
    bot_summary: str
    bot_keywords: list[str]
    text: str