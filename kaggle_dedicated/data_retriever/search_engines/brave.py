from typing import cast, Optional, Literal
from datetime import datetime, timezone
import os
import aiohttp
from unidecode import unidecode
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

from ..schema import SearchResult, AbstractSearchEngine

SEARCH_QUERY = "(inurl:uet.udn.vn OR inurl:edu.vn OR inurl:ajc.hcma OR inurl:hvta.toaan.gov OR inurl:hcmcons.vn OR inurl:hanu.vn OR inurl:hiu.vn OR inurl:vju.ac) {query}"# from ..schema import AbstractSearchEngine, SearchResult
class BraveSearchEngine(AbstractSearchEngine):
    def __init__(self) -> None:
        super().__init__()
    def _to_ascii(self, query: str):
        return unidecode(query)
    def _construct_domain_restrict_query(self, query: str) -> str:
        engine_query = SEARCH_QUERY.format(query=query)
        return engine_query
    def _construct_school_domains_query(self, query: str, domains: list[str]) -> str:
        if len(domains) == 0: return query
        domain_queries = []
        for domain in domains:
            domain_queries.append(f"inurl:{domain}")
        engine_query = "(" + " OR ".join(domain_queries) + ") " + query
        return engine_query
    def _construct_freshness(self, time_metric: Literal["d", "m", "y"], time_range: int) -> str:
        today = datetime.now(timezone.utc)
        if time_metric == "y":
            time_span = timedelta(days=365*time_range)
        elif time_metric == "m":
            time_span = timedelta(days=30*time_range)
        else:
            time_span = timedelta(days=time_range)
        from_day = today - time_span
        return from_day.strftime("%Y-%m-%d") + "to" + today.strftime("%Y-%m-%d")
    async def search(
        self, 
        query: str, 
        domain_restrict: Optional[bool], 
        school_domains: Optional[list[str]], 
        time_metric: Optional[Literal["d", "m", "y"]], 
        time_range: Optional[int]
    ) -> list[SearchResult]:
        k = 10
        if school_domains:
            engine_query = self._construct_school_domains_query(query, school_domains)
        elif domain_restrict:
            engine_query = self._construct_domain_restrict_query(query)
            k = 20 # Try to get more result, seem like not work anyway
        else:
            engine_query = query
        if time_metric and time_range:
            date_restrict = self._construct_freshness(time_metric, time_range)
        else:
            date_restrict = None
        results = await self._search(
            k,
            query,
            engine_query,
            date_restrict
        )
        if school_domains:
            # Brave may ignore domain restrict when apply freshness, so we filtere in one more time
            filtered_results = []
            for result in results:
                if any([domain in urlparse(result["url"]).netloc for domain in school_domains]):
                    filtered_results.append(result)
            return filtered_results
        else:
            return results
    async def _search(self, k: int, query: str, engine_query: str, freshness: str | None = None):
        # k >= 1
        url = "https://api.search.brave.com/res/v1/web/search"
        api_key = os.getenv("BRAVE_SEARCH_API_KEY")
        if api_key is None:
            print(f"[Search Engine] Error: No Brave search api key found")
            return []
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key}
        params = {
            "q": engine_query,
            "count": k,
            "search_lang": "vi",
            # "country": "VN", # Not support
            "safesearch": "moderate",
            "text_decorations": "false",  # Không cần đánh dấu văn bản
        }
        if freshness:
            params["freshness"] = freshness
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url=url, headers=headers, params=params) as response:
                    if response.ok:
                        data: dict = await response.json()
                        result: list[SearchResult] = []
                        for item in data.get("web", {}).get("results", {}):
                            item: dict
                            search_item: SearchResult = {
                                "query": query,
                                "url": cast(str, item["url"]),
                                "title": cast(str, item.get("title")),
                                "description": cast(str, item.get("description")),
                                "score": 1
                            }
                            result.append(search_item)
                        return result
                    else:
                        print(f"[Search Engine] Error {response.status}: {await response.text()}")
                        return []
        except Exception as e:
            print(f"[Search Engine] Error: {str(e)}")
            return []
