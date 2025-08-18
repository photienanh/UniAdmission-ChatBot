from typing import cast
from datetime import datetime, timezone
import os
import aiohttp
from ..search_query import SEARCH_QUERY
from ..schema import AbstractSearchEngine, SearchResult
# SEARCH_QUERY = "(inurl:udn.vn OR inurl:edu.vn OR inurl:ajc.hcma OR inurl:hvta.toaan.gov OR inurl:hcmcons.vn OR inurl:hanu.vn OR inurl:hiu.vn OR inurl:vju.ac) {query}"# from ..schema import AbstractSearchEngine, SearchResult
# class AbstractSearchEngine:
#     pass
# class SearchResult:
#     pass
class GoogleSearchEngine(AbstractSearchEngine):
    def __init__(self) -> None:
        super().__init__()
        self.query_template = SEARCH_QUERY
    async def search(self, query: str, k: int, domain_restrict: bool) -> list[SearchResult]:
        # 1 <= k <= 10
        api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        cx = os.getenv("GOOGLE_SEARCH_CX")
        if api_key is None:
            print(f"[Search Engine] Error: No Google search api key found")
            return []
        if cx is None:
            print(f"[Search Engine] Error: No Google cx found")
            return []
        result: list[SearchResult] = []
        for start in range(1, k+1, 10):
            cap_result = await self._search_cap_10(start, min(10, k-len(result)), api_key, cx, query, domain_restrict)
            if len(cap_result) == 0:
                break
            else:
                result.extend(cap_result)
        return result
    async def _search_cap_10(self, start: int, k: int, api_key: str, cx: str, query: str, domain_restrict: bool) -> list[SearchResult]:
        url = "https://www.googleapis.com/customsearch/v1"
        if domain_restrict:
            q = self.query_template.format(query=query)
        else:
            q = query
        params = {
            "key": api_key,
            "cx": cx,
            "q": q,
            "num": k,
            "start": start,
            "lr": "lang_vi",
            "cr": "countryVN"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.ok:
                        data: dict = await response.json()
                        result: list[SearchResult] = []
                        for index, item in enumerate(data.get("items", [])):
                            item: dict
                            search_item: SearchResult = {
                                "url": cast(str, item["link"]),
                                "title": cast(str, item.get("title", "")),
                                "description": cast(str, item.get("snippet", "")),
                                "index": start-1+index,
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
    engine = GoogleSearchEngine()
    results = asyncio.run(engine.search("Điểm chuẩn UET 2025", 20, True))
    with open("results.json", 'w', encoding='utf-8') as file:
        file.write(json.dumps(results))