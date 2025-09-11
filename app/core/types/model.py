import sys
if sys.version_info.minor >= 12:
    from typing import TypedDict
else:
    from typing_extensions import TypedDict
from typing import Literal, Optional, NotRequired, TypeVar
import math
from .rag import WebSource, RagSource, SearchEngineType
class ModelInfo(TypedDict):
    name: str
    id: str

class GenerationParams(TypedDict):
    # Model
    model_id: str
    # Search
    use_websearch: NotRequired[bool]
    use_localdb: NotRequired[bool]
    max_query: NotRequired[int]
    query_score_threshold: NotRequired[float]
    engine_type: NotRequired[SearchEngineType] # google/brave
    domain_restrict: NotRequired[bool]
    school_domain: NotRequired[bool]
    time_metric: NotRequired[Literal["m", "y", "d"]]
    time_range: NotRequired[int]
    # Rerank
    llm_rerank: NotRequired[bool]
    page_score_threshold: NotRequired[float]
    chunk_score_threshold: NotRequired[float]
    # Retrieve
    k_docs: NotRequired[int]
    k_pages: NotRequired[int]
    page_rerank: NotRequired[bool]
    chunk_rerank: NotRequired[bool]
    include_pdf: NotRequired[bool]
    include_image: NotRequired[bool]
    merge_table: NotRequired[bool]
    merge_neighbor: NotRequired[bool]
    # Sampling
    max_tokens: NotRequired[int]
    temperature: NotRequired[float]
    top_p: NotRequired[float]
    top_k: NotRequired[int]
    # Other
    max_history: NotRequired[int]
    
class ModelPreOutput(TypedDict):
    generation_params: GenerationParams
    web_sources: list[WebSource]
    rag_sources: list[RagSource]
    extra_data: dict
    result_url: str
    
class ModelOutput(ModelPreOutput):
    text: str
    
TNumeric = TypeVar("TNumeric", float, int)
def _clamp(value: TNumeric, low: TNumeric, high: TNumeric) -> TNumeric:
    return max(low, min(value, high))
def server_side_generation_params_validation(params: GenerationParams):
    # Assign params["time_range"] to time_range then check if time_range is not None
    if (time_range := params.get("time_range")) is not None:
        params["time_range"] = _clamp(time_range, 0, 365)
    if (max_tokens := params.get("max_tokens")) is not None:
        params["max_tokens"] = _clamp(max_tokens, 1, 16384)
    if (temperature := params.get("temperature")) is not None:
        params["temperature"] = _clamp(temperature, 0, 1)
    if (top_p := params.get("top_p")) is not None:
        params["top_p"] = _clamp(top_p, 0, 1)
    if (top_k := params.get("top_k")) is not None:
        params["top_k"] = _clamp(top_k, 1, 256)
    if (max_history := params.get("max_history")) is not None:
        params["max_history"] = _clamp(max_history, 0, 16)
    if (k_pages := params.get("k_pages")) is not None:
        params["k_pages"] = _clamp(k_pages, 0, 10)
    if (k_docs := params.get("k_docs")) is not None:
        params["k_docs"] = _clamp(k_docs, 0, 30)