from langchain_core.documents import Document

from ..config import SplitterConfig
from ..utils import TokenMarkdownSplitter

class Splitter:
    def __init__(self, config: SplitterConfig) -> None:
        self.splitter = TokenMarkdownSplitter(tokenizer_name=config.tokenizer_name, device=config.device ,chunk_size=config.chunk_size, chunk_overlap=config.chunk_overlap)
        self.logging = True
    def __call__(self, docs: list[Document]) -> list[Document]:
        """Accept a list of page `Document`. Split and return a list of webpage content, in `Document` format. Return a list of chunks in `Document` format."""
        total_chunks = []
        for page_doc in docs: # Page index may be shuffled by reranker, so we don't use enumerate
            page_metadata = page_doc.metadata
            chunks = self.splitter.split_text(page_doc.page_content) # Not need split_documents, since we handle metadata manully
            if self.logging:
                print(f"Split {len(page_doc.page_content)} characters to {len(chunks)} chunks")
            chunk_index = 0
            for chunk_index, chunk in enumerate(chunks):
                metadata = {
                    "title": page_metadata["title"],
                    "url": page_metadata["url"],
                    "page_index": page_metadata["page_index"],
                    "chunk_index": chunk_index
                }
                # Create new `Document` for this chunk
                doc = Document(
                    page_content=chunk,
                    metadata=metadata
                )
                total_chunks.append(doc)
            last_chunk_index = chunk_index
            # Handle files
            file_docs: list[Document] = page_metadata["files"]
            file_chunks = self.splitter.split_documents(file_docs)
            for file_index, chunk in enumerate(file_chunks):
                chunk_index = last_chunk_index + file_index
                metadata = chunk.metadata
                metadata.update({
                    "title": page_metadata["title"],
                    "url": page_metadata["url"],
                    "page_index": page_metadata["page_index"],
                    "chunk_index": chunk_index
                })
                doc = Document(
                    page_content=chunk.page_content,
                    metadata=metadata
                )
                total_chunks.append(doc)
        if self.logging:
            print(f"Split {len(docs)} pages to {len(total_chunks)} chunks")
        return total_chunks