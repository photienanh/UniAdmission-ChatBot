from dataclasses import dataclass
from typing import Callable, Awaitable, TypedDict, Literal

FILE_PREFIX = "[{title}]({url}):\n"

@dataclass
class WebsearchConfig:
    page_timeout: float = 10
    file_timeout: float = 5
    concurrent_page: int = 4
    concurrent_download: int = 16
    
@dataclass
class MergeNeighborConfig:
    k_previous_chunks: int = 1
    k_next_chunks: int = 1

@dataclass
class MergeTableConfig:
    k_max_previous: int = 5
    k_max_next: int = 5
    separator_threshold: int = 1
    
@dataclass
class RagConfig:
    embedding_name: str = "intfloat/multilingual-e5-base"
    device: str = "cpu"
    
@dataclass
class SplitterConfig:
    tokenizer_name: str = "Qwen/Qwen3-4B"
    chunk_size: int = 512
    chunk_overlap: int = 16
    min_chunk_length: int = 5
    device: str = "cpu"
    
@dataclass
class ChunkRankerConfig:
    ranker_name: str = "ms-marco-MultiBERT-L-12"
    max_length: int = 512
    keep_order: bool = True
    
@dataclass
class PageRankerConfig:
    """Safe to assign `call` later"""
    use_llm: bool = True # Only valid when `call` is not `None``
    call: Callable[[str, list[tuple[str, str]]], Awaitable[list[float]]] | None = None
    
    