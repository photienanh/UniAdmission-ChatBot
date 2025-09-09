from typing import Protocol
from ..schema import SearchResult

from server import GenerationParams

class PageRerankModelProtocol(Protocol):
    async def rerank_page(self, pages: list[SearchResult], query: str, relative_threshold: float, params: GenerationParams) -> list[SearchResult]:
        """
        Perform llm rerank with pages.
        """
        raise NotImplementedError()