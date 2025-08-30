import sys
if sys.version_info.minor >= 12:
    from typing import TypedDict, Optional, List
else:
    from typing_extensions import TypedDict, Optional, List
from core.types import GenerationParams, KaggleServerInfo

    
class APIJobInfo(TypedDict):
    model_id: str
    conversation: List[dict]  # List of {"role": str, "content": str}
    sampling_params: GenerationParams
    web_sources: Optional[list]  # For passing cached web sources if available
    session_id: Optional[str]  # Add session_id for multi-turn conversation
    
class ServerStatus(TypedDict):
    info: KaggleServerInfo
    timestamp: float
    