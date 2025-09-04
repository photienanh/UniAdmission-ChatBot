from langchain.text_splitter import TokenTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
import time
from langchain_core.documents import Document
from typing import Literal

from .schema import RagSource, WebSource, SearchEngineType
from .pipeline import SearchPipeline

FILE_TEMPLATE = "[**{source_title}**]({source_url}):[{title}]({url})\n"

class CmdLogger:
    def __init__(self, prefix: str) -> None:
        self._prefix = prefix
        self._enable = True
        self._enable_time = True
        self._start_time = 0
    def start(self):
        self._start_time = time.time()
    def end(self, message: str):
        if self._enable_time:
            print(f"[{self._prefix}] {message}: {time.time() - self._start_time:.5f}s")
    def log(self, message: str):
        if self._enable:
            print(f"[{self._prefix}] {message}")
class Websearch:
    def __init__(self,
            embedding_name: str, 
            device: str = "cpu",
            chunk_size: int = 1024, 
            chunk_overlap: int = 128,
            page_timeout: float = 10,
            file_timeout: float = 10,
            concurrent_page: int = 4,
            concurrent_file_download: int = 16
        ) -> None:
        self.embedding = HuggingFaceEmbeddings(model_name=embedding_name, model_kwargs={"device":device})
        self.web_search = SearchPipeline(
            page_timeout=page_timeout,
            file_timeout=file_timeout,
            concurrent_page=concurrent_page,
            concurrent_processor_download=concurrent_file_download
        )
        self.splitter = TokenTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.logger = CmdLogger("Web search")
    def __del__(self):
        del self.embedding
        del self.splitter
    
    async def start(self):
        await self.web_search.start()
    def chunk_with_table_protection(self, text: str, max_lines: int = 70, overlap: int = 5, table_preview: int = 5):
        """Chunk text while protecting table structure with overlap and preview"""
        lines = text.splitlines()
        chunks = []
        current = []
        table_buffer = []
        in_table = False

        for i, line in enumerate(lines):
            # detect bảng bắt đầu
            if "<!--TABLE_START-->" in line:
                if current:
                    preview = lines[i+1 : i+1+table_preview] if i+1 < len(lines) else []
                    chunks.append("\n".join(current + preview))
                    current = []

                in_table = True
                table_buffer = []
                continue

            # detect bảng kết thúc
            if "<!--TABLE_END-->" in line:
                # đóng bảng
                table_chunk = "\n".join(table_buffer).strip()
                if table_chunk:  # Only add non-empty table chunks
                    chunks.append(table_chunk)

                in_table = False
                table_buffer = []

                # giữ overlap từ cuối bảng → chunk sau
                current = table_chunk.splitlines()[-overlap:] if overlap > 0 and table_chunk else []
                continue

            # trong bảng
            if in_table:
                table_buffer.append(line)
            else:
                current.append(line)
                if len(current) >= max_lines:
                    chunks.append("\n".join(current))
                    # giữ overlap cho text
                    current = current[-overlap:] if overlap > 0 else []

        # chốt lại chunk cuối
        if current:
            chunks.append("\n".join(current))

        # Return simple list of content strings (no need for dict format here)
        return [chunk.strip() for chunk in chunks if chunk.strip()]

    def rerank_chunks(self, relevant_chunks: list[tuple[Document, float]], k_docs: int) -> list[Document]:
        reranked = []
        for doc, score in relevant_chunks:
            similarity = 1 / (1 + score)
            if doc.metadata.get("protected_table", False):
                similarity *= 1.5
            
            reranked.append((doc, similarity))
            reranked.sort(key=lambda x: x[1], reverse=True)
            result = [doc for doc, _ in reranked]
        return result[:k_docs]

    async def _search_to_docs(
        self, 
        fallback_query: str, 
        k_pages: int, 
        in_domain: bool, 
        engine: SearchEngineType = "brave",
        include_pdf: bool = False,
        include_image: bool = False,
        web_keywords: list[str] = None
    ) -> list[Document]:
        # Use provided web_search_keywords if available, otherwise use fallback_query
        if web_keywords and len(web_keywords) > 0:
            search_results = []
            # Search with each keyword separately using pipeline
            keyword_results = await self.web_search.call_fast(
                fallback_query, k_pages, in_domain, engine, include_pdf, include_image, 
                external_keywords=web_keywords
            )
            search_results = keyword_results
        else:
            print(f"[WebSearch] No generated keywords, using fallback query: '{fallback_query}'")
            search_results = await self.web_search.call_fast(fallback_query, k_pages, in_domain, engine, include_pdf, include_image)
        docs: list[Document] = []
        for search_result in search_results:
            doc_meta: dict = {
                "title": search_result["title"],
                "url": search_result["url"],
                "description": search_result["description"],
                "timestamp": search_result["timestamp"],
                "content": ""
            }
            pdf_content = []
            image_content = []
            for file in search_result["pdf_content"]:
                content = FILE_TEMPLATE.format(
                    source_title=search_result["title"],
                    source_url=search_result["url"],
                    title=file["title"],
                    url=file["url"]
                )
                pdf_content.append(content)
            for file in search_result["image_content"]:
                content = FILE_TEMPLATE.format(
                    source_title=search_result["title"],
                    source_url=search_result["url"],
                    title=file["title"],
                    url=file["url"]
                )
                image_content.append(content)
            content = search_result["main_content"]
            if len(pdf_content) > 0:
                content += "\n" + "\n".join(pdf_content)
            if len(image_content) > 0:
                content += "\n" + "\n".join(image_content)
            doc = Document(
                page_content=content,
                metadata=doc_meta
            )
            docs.append(doc)
        return docs
    
    async def __call__(
        self,
        fallback_query: str, 
        k_pages: int, 
        k_docs: int, 
        domain_restrict: bool, 
        engine: Literal["google", "brave"] = "brave",
        include_pdf: bool = False,
        include_image: bool = False,
        web_keywords: list[str] = None
    ) -> tuple[list[WebSource], list[RagSource]]: 
        docs = await self._search_to_docs(fallback_query, k_pages, domain_restrict, engine, include_pdf, include_image, web_keywords)
        
        # Use table-protected chunking instead of regular splitter
        chunks = []
        for doc in docs:
            # Check if document has table markers
            if "<!--TABLE_START-->" in doc.page_content or "<!--TABLE_END-->" in doc.page_content:
                # Use table-protected chunking with overlap and preview
                doc_chunks = self.chunk_with_table_protection(
                    doc.page_content, 
                    max_lines=50, 
                    overlap=5,  # 5 lines overlap between chunks
                    table_preview=5  # 5 lines preview of table in previous chunk
                )
                for i, chunk_content in enumerate(doc_chunks):
                    chunk_doc = Document(
                        page_content=chunk_content,
                        metadata={**doc.metadata, "protected_table": True}
                    )
                    chunks.append(chunk_doc)
            else:
                # Use regular splitter for documents without tables
                regular_chunks = self.splitter.split_documents([doc])
                for chunk in regular_chunks:
                    chunk.metadata["protected_table"] = False
                chunks.extend(regular_chunks)
        
        # Add title to each chunk for better context
        for i, chunk in enumerate(chunks):
            title = chunk.metadata.get("title", "")
            chunk.metadata["chunk_id"] = i
            if title:
                chunk.page_content = f"[{title}]\n{chunk.page_content}"
        
        vector_storage = FAISS.from_documents(chunks, self.embedding)
        
        # Use web keywords for RAG retrieval if available, otherwise fallback to original query
        relevant_chunks = []
        if web_keywords and len(web_keywords) > 0:
            # Multiple retrievals with different keywords
            chunks_per_keyword = max(1, k_docs // len(web_keywords))
            for keyword in web_keywords:
                keyword_chunks = vector_storage.similarity_search_with_score(keyword, k=chunks_per_keyword*2)
                relevant_chunks.extend(self.rerank_chunks(keyword_chunks, chunks_per_keyword))
            
            # If we got more chunks than requested, limit to k_docs
            if len(relevant_chunks) > k_docs:
                relevant_chunks = relevant_chunks[:k_docs]
        else:
            # Fallback to original query
            relevant_chunks = vector_storage.similarity_search_with_score(fallback_query, k=k_docs)
            relevant_chunks = self.rerank_chunks(relevant_chunks)
        
        web_sources: list[WebSource] = []
        rag_sources: list[RagSource] = []
        
        for doc in docs:
            web_source: WebSource = {
                "url": doc.metadata["url"],
                "title": doc.metadata["title"],
                "description": doc.metadata["description"],
                "text": doc.page_content
            }
            web_sources.append(web_source)
            
        # Group chunks by title and merge them
        from collections import defaultdict
        
        grouped = defaultdict(list)
        for chunk in relevant_chunks:
            title = chunk.metadata.get("title", "Untitled")
            grouped[title].append(chunk)
        
        # Sort chunks by chunk_id to maintain order
        for title in grouped:
            grouped[title] = sorted(grouped[title], key=lambda x: x.metadata.get("chunk_id", 0))

        for title, chunk_list in grouped.items():
            # Sort by chunk_id if available
            chunk_list = sorted(chunk_list, key=lambda x: x.metadata.get("chunk_id", 0))
            
            # Merge content with separator, remove title prefix from each chunk
            merged_text = "\n\n---\n\n".join(c.page_content.replace(f"[{title}]\n","") for c in chunk_list)
            
            rag_source: RagSource = {
                "url": chunk_list[0].metadata.get("url", ""),  # Use first chunk's URL
                "title": title,
                "text": merged_text
            }
            rag_sources.append(rag_source)
            
        return web_sources, rag_sources