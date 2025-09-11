from typing import TypedDict, Optional, Literal, NotRequired
    
# Stage 1: Search from API
class SearchResult(TypedDict):
    query: str
    url: str
    title: str
    description: str
    score: float

# Stage 2: Download page (After filter / rerank)
class HtmlResult(SearchResult):
    html: str
    score: float
    
# Stage 3: Process all
from server import WebSource, RagSource, FileSource

SearchEngineType = Literal["google", "brave"]

class AbstractSearchEngine:
    def __init__(self) -> None:
        pass
    async def search(
        self, 
        query: str, 
        domain_restrict: Optional[bool], 
        school_domains: Optional[list[str]], 
        time_metric: Optional[Literal["d", "m", "y"]], 
        time_range: Optional[int]
    ) -> list[SearchResult]:
        """
        Performce search on engine.\n
        Will return 10 results. 
        Args:
            query (str): web query
            domain_restrict (bool): restrict on official domain (like .edu), ignored when use with `school_domains`
            school_domains (list[str]): restrict on specific domains
            time_metric (Literal[&quot;m&quot;, &quot;y&quot;, &quot;h&quot;]): year, month or day
            time_range (int): amount of timespan, like 8d, 7y, 6m.

        Returns:
            list[SearchResult]: list of `SearchResult`
        """
        raise NotImplementedError()
    
