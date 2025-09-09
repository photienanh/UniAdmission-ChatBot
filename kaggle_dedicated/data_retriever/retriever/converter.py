from typing import Any
from langchain_core.documents import Document
from ..schema import RagSource, WebSource, FileSource
from ..config import FILE_PREFIX

class WebSourceToDocumentConverter:
    def __init__(self) -> None:
        pass
    def convert(self, data: WebSource) -> Document:
        """
        Convert `WebSource` into `LangChain` `Document`.\n
        File data stored in `files` as `list` of `Document`
        """
        file_docs: list[Document] = []
        for file in data["files"]:
            file_metadata = {
                "file_title": file["file_title"],
                "file_url": file["file_url"],
                "file_type": file["file_type"]
            }
            file_doc = Document(
                page_content=file["text"],
                metadata=file_metadata
            )
            file_docs.append(file_doc)
        metadata: dict = {
            "title": data["title"],
            "url": data["url"],
            "description": data["description"],
            "files": file_docs
        }
        doc = Document(
            page_content=data["text"],
            metadata=metadata
        )
        return doc
    
class RagSourceToDocumentConverter:
    def revert(self, rag_doc: Document) -> RagSource:
        rag_source: RagSource = {
            "query": rag_doc.metadata["query"],
            "url": rag_doc.metadata["url"],
            "title": rag_doc.metadata["title"],
            "text": rag_doc.page_content,
            "chunk_index": rag_doc.metadata["chunk_index"]
        }
        if "file_type" in rag_doc.metadata:
            rag_source.update({
                "file_title": rag_doc.metadata["file_title"],
                "file_url": rag_doc.metadata["file_url"],
                "file_type": rag_doc.metadata["file_type"]
            })
        return rag_source
    def convert(self, rag_source: RagSource) -> Document:
        rag_metadata = {
            "query": rag_source["query"],
            "url": rag_source["url"],
            "title": rag_source["title"],
            "chunk_index": rag_source["chunk_index"]
        }
        if "file_type" in rag_source:
            rag_metadata.update({
                "file_title": rag_source.get("file_title", ""),
                "file_url": rag_source.get("file_url", ""),
                "file_type": rag_source.get("file_type", "")
            })
        rag_doc = Document(
            page_content=rag_source["text"],
            metadata=rag_metadata
        )
        return rag_doc