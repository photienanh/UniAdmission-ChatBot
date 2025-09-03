import sys
from typing import TypedDict, NamedTuple, Optional, Literal, NotRequired

class FileContent(TypedDict):
    file_type: Literal["pdf", "image"]
    title: str
    parent_url: str
    url: str
    text: str
    
    
class UrlContent(TypedDict):
    title: str
    url: str
    url_type: Literal["pdf", "image", "ref"]

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
    file_urls: list[UrlContent]
    
# Stage 4: Process all
class ProcessedResult(HtmlResult):
    main_content: str
    file_contents: list[FileContent]
    
SearchEngineType = Literal["google", "brave"]

class RagSource(TypedDict):
    url: str
    title: str
    text: str
    file_url: NotRequired[str]
    file_title: NotRequired[str]
    file_type: NotRequired[str]

class FileSource(TypedDict):
    file_url: str
    file_title: str
    file_type: str
    text: str
    
class WebSource(TypedDict):
    url: str
    title: str
    description: str
    text: str
    files: list[FileSource]

    
class AbstractSearchEngine:
    def __init__(self) -> None:
        pass
    async def search(self, query: str, k: int, domain_restrict: bool) -> list[SearchResult]:
        raise NotImplementedError()
    
