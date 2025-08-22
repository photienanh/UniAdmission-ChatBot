import sys
if sys.version_info.minor >= 12:
    from typing import TypedDict
else:
    from typing_extensions import TypedDict
from core.types import GenerationParams, KaggleServerInfo

    
class APIJobInfo(TypedDict):
    model_id: str
    text: str
    sampling_params: GenerationParams
    web_sources: list  # For storing web search results
    
class ServerStatus(TypedDict):
    info: KaggleServerInfo
    timestamp: float
    