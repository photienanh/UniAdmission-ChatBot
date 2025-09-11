from typing import cast
import os
import aiohttp
from typing import Literal, Optional
from urllib.parse import urlparse


from ..schema import AbstractSearchEngine, SearchResult

SEARCH_QUERY = "(inurl:udn.vn OR inurl:edu.vn OR inurl:ajc.hcma OR inurl:hvta.toaan.gov OR inurl:hcmcons.vn OR inurl:hanu.vn OR inurl:hiu.vn OR inurl:vju.ac) {query}"
class GoogleSearchEngine(AbstractSearchEngine):
    def __init__(self) -> None:
        super().__init__()
    def _construct_domain_restrict_query(self, query: str) -> str:
        engine_query = SEARCH_QUERY.format(query=query)
        return engine_query
    def _construct_school_domains_query(self, query: str, domains: list[str]) -> str:
        if len(domains) == 0: return query
        domain_queries = []
        for domain in domains:
            domain_queries.append(f"site:{domain}")
        engine_query = "(" + " OR ".join(domain_queries) + ") " + query
        return engine_query
    
    async def search(
        self, 
        query: str, 
        domain_restrict: Optional[bool], 
        school_domains: Optional[list[str]], 
        time_metric: Optional[Literal["d", "m", "y"]], 
        time_range: Optional[int]
    ) -> list[SearchResult]:
        """May return url of pdf files (or files in general)"""
        if school_domains:
            engine_query = self._construct_school_domains_query(query, school_domains)
        elif domain_restrict:
            engine_query = self._construct_domain_restrict_query(query)
        else:
            engine_query = query
        if time_metric and time_range:
            date_restrict = time_metric+str(time_range)
        else:
            date_restrict = None
        results = await self._search(
            10,
            query,
            engine_query,
            date_restrict
        )
        if school_domains:
            # Google may ignore domain restrict when apply dateRestrict, so we filtere in one more time
            filtered_results = []
            for result in results:
                if any([domain in urlparse(result["url"]).netloc for domain in school_domains]):
                    filtered_results.append(result)
            return filtered_results
        else:
            return results
    async def _search(self, k: int, query: str, engine_query: str, date_restrict: str | None = None) -> list[SearchResult]:
        # k >= 1
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
            cap_result = await self._search_cap_10(start, min(10, k-len(result)), api_key, cx, query, engine_query, date_restrict)
            if len(cap_result) == 0:
                break
            else:
                result.extend(cap_result)
        return result
    async def _search_cap_10(self, start: int, k: int, api_key: str, cx: str, query: str, engine_query: str,  date_restrict: str | None = None) -> list[SearchResult]:
        """Due to google limit max search results of each time to 10, we need to separate it into steps."""
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": cx,
            "q": engine_query,
            "num": k,
            "start": start,
            "lr": "lang_vi",
            "cr": "countryVN"
        }
        if date_restrict:
            params["dateRestrict"] = date_restrict
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.ok:
                        data: dict = await response.json()
                        result: list[SearchResult] = []
                        import json
                        with open("pie.json", 'w', encoding='utf-8') as file:
                            file.write(json.dumps(data.get("items", []), ensure_ascii=False))
                        for item in data.get("items", []):
                            item: dict
                            search_item: SearchResult = {
                                "query": query,
                                "url": cast(str, item["link"]),
                                "title": cast(str, item.get("title", "")),
                                "description": cast(str, item.get("snippet", "")),
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
