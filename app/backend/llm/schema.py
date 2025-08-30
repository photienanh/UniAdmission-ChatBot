import sys
if sys.version_info.minor >= 12:
    from typing import TypedDict, Optional
else:
    from typing_extensions import TypedDict, Optional
from core.types import GenerationParams, WorkerServerInfo

class WorkerStatus(TypedDict):
    info: WorkerServerInfo
    timestamp: float
    