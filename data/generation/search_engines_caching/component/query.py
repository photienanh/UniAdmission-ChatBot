from typing import Literal
from urllib.parse import urlparse


from ..engines import GoogleSearchEngine, BraveSearchEngine
from ..schema import SearchResult, AbstractSearchEngine
from ..netloc import WHITE_LIST
class WebQuery:
    def __init__(self) -> None:
        self.engines: dict[str, AbstractSearchEngine] = {
            "google": GoogleSearchEngine(),
            "brave": BraveSearchEngine()
        }
        self.white_list = WHITE_LIST
    async def __call__(self, 
            query: str, 
            k: int, 
            in_domain: bool = False, 
            engine_type: Literal["brave", "google"] = "brave", 
        ) -> list[SearchResult]:  
        result = await self.engines[engine_type].search(query, k, in_domain)
        return result