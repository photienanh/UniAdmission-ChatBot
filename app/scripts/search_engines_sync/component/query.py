import requests
from ..engines import SearchResult, HtmlResult, GoogleSearchEngine, BraveSearchEngine, AbstractSearchEngine
from typing import Literal
from ..netloc import WHITE_LIST
from urllib.parse import urlparse

class WebQuery:
    def __init__(self) -> None:
        self.engines: dict[str, AbstractSearchEngine] = {
            "google": GoogleSearchEngine(),
            "brave": BraveSearchEngine()
        }
        self.white_list = WHITE_LIST
    def __call__(self, query: str, k: int = 10, in_domain: bool = False, engine_type: Literal["brave", "google"] = "brave") -> list[SearchResult | None]:
        search_result = self.engines[engine_type].search(query, k)
        result = []
        for item in search_result:
            if in_domain:
                valid = False
                for netloc in self.white_list:
                    parsed = urlparse(item["url"])
                    if netloc in parsed.netloc:
                        valid = True
                        break
                if not valid:
                    item = None
            result.append(item)
        return result