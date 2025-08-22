from typing import cast
from datetime import datetime, timezone
import os
import aiohttp
from unidecode import unidecode

from ..search_query import SEARCH_QUERY    
from ..schema import SearchResult, AbstractSearchEngine
# SEARCH_QUERY = "(inurl:uet.udn.vn OR inurl:edu.vn OR inurl:ajc.hcma OR inurl:hvta.toaan.gov OR inurl:hcmcons.vn OR inurl:hanu.vn OR inurl:hiu.vn OR inurl:vju.ac) {query}"# from ..schema import AbstractSearchEngine, SearchResult
# class AbstractSearchEngine:
#     pass
# class SearchResult:
#     pass

class BraveSearchEngine(AbstractSearchEngine):
    def __init__(self) -> None:
        super().__init__()
        self.query_template = SEARCH_QUERY.replace("inurl:", "site:")
    def _to_ascii(self, query: str):
        return unidecode(query)
    async def search(self, query: str, k: int, domain_restrict: bool):
        # 1 <= k
        url = "https://api.search.brave.com/res/v1/web/search"
        if domain_restrict:
            q = self.query_template.format(query=self._to_ascii(query))
        else:
            q = query
        api_key = os.getenv("BRAVE_SEARCH_API_KEY")
        if api_key is None:
            print(f"[Search Engine] Error: No Brave search api key found")
            return []
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key}
        params = {
            "q": q,
            "count": k,
            "search_lang": "vi",
            # "country": "VN", # Not support
            "safesearch": "moderate",
            "text_decorations": "false",  # Không cần đánh dấu văn bản
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url=url, headers=headers, params=params) as response:
                    if response.ok:
                        data: dict = await response.json()
                        result: list[SearchResult] = []
                        for index, item in enumerate(data.get("web", {}).get("results", {})):
                            item: dict
                            search_item: SearchResult = {
                                "url": cast(str, item["url"]),
                                "title": cast(str, item.get("title")),
                                "description": cast(str, item.get("description")),
                                "index": index,
                                "timestamp": datetime.now(timezone.utc).isoformat()   
                            }
                            result.append(search_item)
                        return result
                    else:
                        print(f"[Search Engine] Error {response.status}: {await response.text()}")
                        return []
        except Exception as e:
            print(f"[Search Engine] Error: {str(e)}")
            return []
if __name__ == "__main__":
    import asyncio, json
    engine = BraveSearchEngine()
    results = asyncio.run(engine.search("Điểm chuẩn UET 2025", 10, True))
    with open("results.json", 'w', encoding='utf-8') as file:
        file.write(json.dumps(results))

