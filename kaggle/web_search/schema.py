from typing import TypedDict, Optional, Literal

class FileContent(TypedDict):
    title: str
    parent_url: str
    url: str
    text: str
    
class UrlContent(TypedDict):
    title: str
    url: str

# Stage 1: Search from API
class SearchResult(TypedDict):
    url: str
    title: str
    description: str
    timestamp: str
    index: int

# Stage 2: Download page
class HtmlResult(SearchResult):
    html: str

# Stage 3: Extract content and link
class PreProcessedResult(HtmlResult):
    extracted_content: str
    
    ref_urls: list[UrlContent]
    image_urls: list[UrlContent]
    pdf_urls: list[UrlContent]
    
# Stage 4: Process all
class ProcessedResult(HtmlResult):
    main_content: str
    image_content: list[FileContent]
    pdf_content: list[FileContent]
    
SearchEngineType = Literal["google", "brave"]

class RagSource(TypedDict):
    url: str
    title: str
    text: str
class WebSource(TypedDict):
    url: str
    title: str
    description: str
    text: str
    
class AbstractSearchEngine:
    def __init__(self) -> None:
        pass
    async def search(self, query: str, k: int, domain_restrict: bool) -> list[SearchResult]:
        raise NotImplementedError()
    
