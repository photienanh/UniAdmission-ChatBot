import requests
from ..engines import SearchResult, HtmlResult, GoogleSearchEngine, BraveSearchEngine, AbstractSearchEngine
from typing import Literal

class WebQuery:
    def __init__(self) -> None:
        self.engines: dict[str, AbstractSearchEngine] = {
            "google": GoogleSearchEngine(),
            "brave": BraveSearchEngine()
        }
    def __call__(self, query: str, k: int = 10, engine_type: Literal["brave", "google"] = "brave") -> list[SearchResult | None]:
        result = self.engines[engine_type].search(query, k)
        return [r for r in result]
