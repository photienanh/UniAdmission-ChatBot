import requests
from ..config import GOOGLE_API_KEY as API_KEY
from ..config import GOOGLE_CX as CX
from .data import AbstractSearchEngine, SearchResult
from typing import cast
from datetime import datetime, timezone

class GoogleSearchEngine(AbstractSearchEngine):
    def __init__(self) -> None:
        super().__init__()
    def search(self, query: str, k: int) -> list[SearchResult]:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": API_KEY,
            "cx": CX,
            "q": query,
            "num": k
        }
        response = requests.get(url, params)
        response.raise_for_status()
        data: dict = response.json()
        result: list[SearchResult] = []
        for index, item in enumerate(data.get("items", [])):
            search_item: SearchResult = {
                "url": cast(str, item["link"]),
                "title": cast(str, ["title"]),
                "description": cast(str, ["snippet"]),
                "index": index,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            result.append(search_item)
        return result
    
if __name__ == "__main__":
    engine = GoogleSearchEngine()
    import json
    results = engine.search("Điểm chuẩn UET", 3)
    with open("results.json", 'w', encoding='utf-8') as file:
        file.write(json.dumps(results))