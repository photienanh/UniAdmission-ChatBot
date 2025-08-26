from .lang_extra import TokenMarkdownSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
import time
from langchain_core.documents import Document
from typing import Literal
from flashrank import Ranker, RerankRequest
import copy

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
            tokenizer_name: str, 
            ranker_name: str,
            device: str = "cpu",
            chunk_size: int = 512, 
            chunk_overlap: int = 32,
            page_timeout: float = 10,
            file_timeout: float = 10,
            concurrent_page: int = 4,
            concurrent_file_download: int = 16
        ) -> None:
        if chunk_size > 512:
            raise ValueError(f"Chunk size must be equal or less than 512, currently: {chunk_size}")
        self.embedding = HuggingFaceEmbeddings(model_name=embedding_name, model_kwargs={"device":device})
        self.web_search = SearchPipeline(
            page_timeout=page_timeout,
            file_timeout=file_timeout,
            concurrent_page=concurrent_page,
            concurrent_processor_download=concurrent_file_download
        )
        self.splitter = TokenMarkdownSplitter(tokenizer_name=tokenizer_name, device=device ,chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.ranker = Ranker(ranker_name, max_length=chunk_size)
        self.logger = CmdLogger("Web search")
    def __del__(self):
        del self.embedding
        del self.splitter
    async def start(self):
        await self.web_search.start()
    async def _search_to_pages(
        self, 
        query: str, 
        k_pages: int, 
        in_domain: bool, 
        engine: SearchEngineType = "brave",
        include_pdf: bool = False,
        include_image: bool = False
    ) -> list[Document]:
        """Websearch and return a list of `Document`, each `Document` contain a single web page"""
        self.logger.start()
        # Call Google/Brave search engine then process text/pdf/image
        search_results = await self.web_search.call_fast(query, k_pages, in_domain, engine, include_pdf, include_image)
        self.logger.end("Web search")
        # Convert to langchain Document format
        docs: list[Document] = []
        for page_index, search_result in enumerate(search_results):
            metadata: dict = {
                "title": search_result["title"],
                "url": search_result["url"],
                "description": search_result["description"],
                "timestamp": search_result["timestamp"],
                "page_index": page_index
            }
            # Handle pdf and image
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
                metadata=metadata
            )
            docs.append(doc)
        return docs
    def _page_rerank(
        self,
        page_docs: list[Document],
        web_query: str
    ) -> list[Document]:
        """Perform rerank with relevant chunks from vectordb search. Change page index inside it, old page index still keep as `old_page_idex` field."""
        # For lookup when process result
        id_pages = {index: chunk for index, chunk in enumerate(page_docs)} 
        # Convert to flashrank format
        print("---Original order ---")
        for doc in page_docs:
            print(doc.metadata["title"])
        passages = [{
            "id": index,
            "text": f'{page.metadata["title"]}:\n {page.metadata["description"]}',
        } for index, page in enumerate(page_docs)]
        request = RerankRequest(query=web_query, passages=passages)
        results = self.ranker.rerank(request)
        
        reorder_pages: list[Document] = []
        for index, result in enumerate(results):
            page = id_pages[result["id"]]
            page.metadata["old_page_index"] = page.metadata["page_index"]
            page.metadata["page_index"] = index
            reorder_pages.append(page)
            
        print("---Reorder ---")
        for doc in reorder_pages:
            print(doc.metadata["title"])
        return reorder_pages
    def _split_to_chunks(
        self, 
        page_docs: list[Document]
    ) -> list[Document]: 
        """Split and return a list of webpage content, in `Document` format. Return a list of chunks in `Document` format."""
        total_chunks = []
        for page_doc in page_docs: # Page index may be shuffled by reranker, so we don't use enumerate
            page_metadata = page_doc.metadata
            chunks = self.splitter.split_text(page_doc.page_content) # Not need split_documents, since we handle metadata manully
            self.logger.log(f"Split {len(page_doc.page_content)} characters to {len(chunks)} chunks")
            for chunk_index, chunk in enumerate(chunks):
                metadata = {
                    "title": page_metadata["title"],
                    "url": page_metadata["url"],
                    "timestamp": page_metadata["timestamp"],
                    "page_index": page_metadata["page_index"],
                    "chunk_index": chunk_index
                }
                # Create new `Document` for this chunk
                doc = Document(
                    page_content=chunk,
                    metadata=metadata
                )
                total_chunks.append(doc)
        print(f"Split {len(page_docs)} pages to {len(total_chunks)} chunks")
        return total_chunks
    def _faiss_search(
        self,
        chunks: list[Document],
        rag_query: str,
        k_chunks: int
    ) -> list[Document]:
        """Perform rag search with chunks, return a list of relevant chunks"""
        vector_storage = FAISS.from_documents(chunks, self.embedding)
        relevant_chunks = vector_storage.as_retriever(search_kwargs={"k": k_chunks}).invoke(rag_query)
        return relevant_chunks
    def _chunk_rerank(
        self,
        chunks: list[Document],
        rerank_query: str,
        rerank_relative_threshold: float = 0.5,
        preserve_order: bool = True
    ) -> list[Document]:
        """Perform rerank with relevant chunks from vectordb search"""
        # For lookup when process result
        id_chunks = {index: chunk for index, chunk in enumerate(chunks)} 
        # Convert to flashrank format
        passages = [{
            "id": index,
            "text": chunk.page_content
        } for index, chunk in enumerate(chunks)]
        request = RerankRequest(query=rerank_query, passages=passages)
        results = self.ranker.rerank(request)
        max_score = 0
        for result in results:
            max_score = max(max_score, result["score"])
        score_threshold = 0 if max_score == 0 else max_score * rerank_relative_threshold
        
        valid_chunks: list[Document] = []
        for result in results:
            if result["score"] >= score_threshold:
                valid_chunks.append(id_chunks[result["id"]])
        if not preserve_order:
            return valid_chunks
        else:
            return sorted(valid_chunks, key=lambda x: (x.metadata["page_index"], x.metadata["chunk_index"]))
    def _neighbor_search(
        self,
        total_chunks: list[Document],
        relevant_chunks: list[Document],
        k_previous_neighbor: int,
        k_next_neighbor: int
    ) -> list[Document]:
        result: list[Document] = []
        """Retrive neighbor chunks to relevant chunks."""
        # Mapping table for lookup with page and chunk index
        lookup_table = {
            (chunk.metadata["page_index"], chunk.metadata["chunk_index"]): chunk for chunk in total_chunks
        }
        # Mark retrived key
        retrived_keys: set[tuple[int, int]] = set()
        result: list[Document] = []
        for chunk in relevant_chunks:
            page_index = chunk.metadata["page_index"]
            chunk_index = chunk.metadata["chunk_index"]
            from_ = max(0, chunk_index-k_previous_neighbor)
            to_ = chunk_index + k_next_neighbor + 1 # We don't know max length
            for current_index in range(from_, to_):
                key = (page_index, current_index)
                if key in lookup_table and key not in retrived_keys:
                    retrived_keys.add(key)
                    result.append(lookup_table[key])
        return result
    async def __call__(
        self,
        web_query: str, 
        rag_query: str, 
        k_pages: int, 
        k_docs: int, 
        domain_restrict: bool, 
        engine: Literal["google", "brave"] = "brave",
        include_pdf: bool = False,
        include_image: bool = False,
        use_rerank_page: bool = False,
        use_rerank_chunk: bool = False,
        rerank_relative_threshold: float = 0.5,
        preserve_rerank_order: bool = True,
        neighbor_previous_k: int = 1,
        neighbor_next_k: int = 1,
        min_chunk_char_length: int = 5 # Not implemeted
    ) -> tuple[list[WebSource], list[RagSource]]: 
        """
        Reranker will use `web_query`
        """
        webpage_docs = await self._search_to_pages(web_query, k_pages, domain_restrict, engine, include_pdf, include_image)
        if use_rerank_page:
            webpage_docs = self._page_rerank(webpage_docs, web_query)
        total_chunks = self._split_to_chunks(webpage_docs)
        relevant_chunks = self._faiss_search(total_chunks, rag_query, k_docs)
        if use_rerank_chunk:
            relevant_chunks = self._chunk_rerank(relevant_chunks, web_query, rerank_relative_threshold, preserve_rerank_order)
        rag_docs = self._neighbor_search(total_chunks, relevant_chunks, neighbor_previous_k, neighbor_next_k)
        
        web_sources: list[WebSource] = []
        rag_sources: list[RagSource] = []
        for webpage_doc in webpage_docs:
            web_source: WebSource = {
                "url": webpage_doc.metadata["url"],
                "title": webpage_doc.metadata["title"],
                "description": webpage_doc.metadata["description"],
                "text": webpage_doc.page_content
            }
            web_sources.append(web_source)
        for rag_doc in rag_docs:
            rag_source: RagSource = {
                "url": rag_doc.metadata["url"],
                "title": rag_doc.metadata["title"],
                "text": rag_doc.page_content
            }
            rag_sources.append(rag_source)
        
        return web_sources, rag_sources
