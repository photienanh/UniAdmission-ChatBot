from typing import TypedDict

from .model import ModelInfo, ModelPreOutput, GenerationParams

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