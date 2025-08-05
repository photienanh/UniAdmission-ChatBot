import requests
from urllib.parse import urlparse
import json
from .data import SearchResult, AbstractSearchEngine
from ..config import BRAVE_API_KEY
from typing import cast
from datetime import datetime, timezone
    
class BraveSearchEngine(AbstractSearchEngine):
    def __init__(self) -> None:
        super().__init__()
    def search(self, query: str, k: int):
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": BRAVE_API_KEY}
        params = {
            "q": query,
            "count": k,
            "search_lang": "vi",  # Vietnamese language
            "safesearch": "moderate",
            "text_decorations": "false",  # Không cần đánh dấu văn bản
        }
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        result: list[SearchResult] = []
        for index, item in enumerate(data["web"]["results"]):
            url = item["url"]
            search_item: SearchResult = {
                "url": cast(str, item["url"]),
                "title": cast(str, item["title"]),
                "description": cast(str, item["description"]),
                "index": index,
                "timestamp": datetime.now(timezone.utc).isoformat()   
            }
            result.append(search_item)
        return result
if __name__ == "__main__":
    engine = BraveSearchEngine()
    results = engine.search("Điểm chuẩn UET", 3)
    with open("results.json", 'w', encoding='utf-8') as file:
        file.write(json.dumps(results))

