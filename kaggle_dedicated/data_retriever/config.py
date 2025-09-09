from dataclasses import dataclass
from typing import Callable, Awaitable, TypedDict, Literal

FILE_PREFIX = "[{title}]({url}):\n"

@dataclass
class WebsearchConfig:
    page_timeout: float = 10
    file_timeout: float = 5
    max_file_per_page: int = 10
    
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
    embedding_name: str = "intfloat/multilingual-e5-small"
    device: str = "cuda"
    keep_order: bool = True
    
@dataclass
class SplitterConfig:
    tokenizer_name: str = "Qwen/Qwen3-4B"
    chunk_size: int = 512
    chunk_overlap: int = 16
    min_chunk_length: int = 5
    device: str = "cuda"
    
@dataclass
class ChunkRankerConfig:
    ranker_name: str = "ms-marco-MultiBERT-L-12"
    max_length: int = 512
    keep_order: bool = True
    
@dataclass
class DataRetrieverConcurrentConig:
    engine_query_limit: int = 1 # There is threshold limit for free tier, so do not increase this
    page_rerank_limit: int = 2
    
    page_download_limit: int = 4
    file_download_limit: int = 16
