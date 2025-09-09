from ..schema import WebSource, RagSource, FileSource
from ..config import SplitterConfig
from .utils import TokenMarkdownSplitter

# This and Rag Retriever Module is only parts that use langchain

class Splitter:
    def __init__(self, config: SplitterConfig) -> None:
        self.splitter = TokenMarkdownSplitter(tokenizer_name=config.tokenizer_name, device=config.device ,chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap)
        self.logging = True
    def split(self, web_source: WebSource) -> list[RagSource]:
        """Split `WebSource` to `RagSource`"""
        chunks = self.splitter.split_text(web_source["text"])
        if self.logging:
            print(f'Split {len(web_source["text"])} characters to {len(chunks)} chunks')
        rag_sources: list[RagSource] = []
        for chunk in chunks:
            rag_source: RagSource = {
                "query": web_source["query"],
                "title": web_source["title"],
                "url": web_source["url"],
                "text": chunk,
                "chunk_index": len(rag_sources)
            }
            rag_sources.append(rag_source)
        # Handle files
        file_sources: list[FileSource] = web_source["files"]
        for file_source in file_sources:
            file_chunks = self.splitter.split_text(file_source["text"])
            for file_chunk in file_chunks:
                rag_source: RagSource = {
                    "query": web_source["query"],
                    "title": web_source["title"],
                    "url": web_source["url"],
                    "text": file_chunk,
                    "chunk_index": len(rag_sources),
                    "file_title": file_source["file_title"],
                    "file_url": file_source["file_url"],
                    "file_type": file_source["file_type"]
                }
        print(f'Split {web_source["title"]} to {len(rag_sources)} chunks')
        return rag_sources