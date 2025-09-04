"""Web search wrapper for easier integration"""

from .web_search import Websearch
from .schema import WebSource, RagSource

class WebSearchWrapper:
    """Wrapper for web search functionality with default configuration"""
    
    def __init__(self) -> None:
        self.web_search = Websearch(
            embedding_name="intfloat/multilingual-e5-small", 
            device="cpu",
            chunk_size=1024, 
            chunk_overlap=128
        )
    
    async def start(self):
        """Initialize the web search"""
        await self.web_search.start()
    
    async def __call__(self, fallback_query: str, params: dict) -> tuple[list[WebSource], list[RagSource]]:
        """Perform web search with given parameters"""
        k_pages = params.get("k_pages", 0)
        k_docs = params.get("k_docs", 0)
        domain_restrict = params.get("domain_restrict", False)
        web_search_keywords = params.get("web_search_keywords", None)
        
        if k_pages == 0 or k_docs == 0:
            return [], []
        else:
            web_sources, rag_sources = await self.web_search(
                fallback_query=fallback_query,
                k_pages=k_pages,
                k_docs=k_docs,
                domain_restrict=domain_restrict,
                engine="brave",
                include_pdf=False,
                include_image=False,
                web_keywords=web_search_keywords
            )
            return web_sources, rag_sources
