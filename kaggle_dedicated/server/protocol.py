from typing import Protocol, AsyncGenerator
import enum

from .schema import GenerationParams

class CallType(enum.Enum):
    ROUTER = "router"
    KEYWORDS = "keywords"
    RANKER = "page_ranker"
    READER = "reader"
    
class ModelProtocol(Protocol):
    async def __call__(self, call_type: CallType | str, instruction: str, prompt: str, params: GenerationParams) -> AsyncGenerator[str, None]: ...