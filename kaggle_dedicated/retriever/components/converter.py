from typing import Any
from langchain_core.documents import Document
from .web_search import *
from ..config import FILE_PREFIX

class WebsearchToWebSourceConverter:
    def __init__(self) -> None:
        pass
    def __call__(self, data: ProcessedResult) -> WebSource:
        """
        Convert Search result into `WebSource`.\n
        File data stored in `files` as `list` of `FileSource`
        """
        file_sources: list[FileSource] = []
        for file in data["file_contents"]:
            file_source: FileSource = {
                "file_title": file["title"],
                "file_url": file["url"],
                "file_type": file["file_type"],
                "text": file["text"]
            }
            file_sources.append(file_source)
        web_source: WebSource = {
            "title": data["title"],
            "url": data["url"],
            "description": data["description"],
            "text": data["main_content"],
            "files": file_sources
        }
        return web_source

class WebSourceToDocumentConverter:
    def __init__(self) -> None:
        pass
    def __call__(self, index: int, data: WebSource) -> Document:
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
            "page_index": index,
            "files": file_docs
        }
        doc = Document(
            page_content=data["text"],
            metadata=metadata
        )
        return doc
    
class DocumentToRagSourceConverter:
    def __init__(self) -> None:
        pass
    
    def __call__(self, docs: list[Document]) -> list[RagSource]:
        rag_sources: list[RagSource] = []
        for rag_doc in docs:
            rag_source: RagSource = {
                "url": rag_doc.metadata["url"],
                "title": rag_doc.metadata["title"],
                "text": rag_doc.page_content
            }
            if "file_type" in rag_doc.metadata:
                rag_source.update({
                    "file_title": rag_doc.metadata["file_title"],
                    "file_url": rag_doc.metadata["file_url"],
                    "file_type": rag_doc.metadata["file_type"]
                })
            rag_sources.append(rag_source)
        
        return rag_sources
    def revert(self, rag_sources: list[RagSource]) -> list[Document]:
        rag_docs: list[Document] = []
        for rag_source in rag_sources:
            rag_metadata = {
                "url": rag_source["url"],
                "title": rag_source["title"],
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
            rag_docs.append(rag_doc)
        return rag_docs