from typing import TypedDict
from core.types import GenerationParams, KaggleServerInfo

    
class APIJobInfo(TypedDict):
    model_id: str
    text: str
    sampling_params: GenerationParams
    
class ServerStatus(TypedDict):
    info: KaggleServerInfo
    timestamp: float
    