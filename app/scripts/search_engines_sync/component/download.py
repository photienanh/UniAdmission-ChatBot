import requests
from ..engines import SearchResult, HtmlResult

class PageDowloader:
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
    def __html(self, url: str) -> str:
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.text
    
    def __call__(self, input: SearchResult) -> HtmlResult | None:
        result: HtmlResult = {
            **input,
            "html": self.__html(input["url"])
        }
        return result
