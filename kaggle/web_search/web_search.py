from langchain.text_splitter import TokenTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
import time
from langchain_core.documents import Document
from typing import Literal
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
            device: str = "cpu",
            chunk_size: int = 1024, 
            chunk_overlap: int = 128,
            page_timeout: float = 10,
            file_timeout: float = 10,
            concurrent_page: int = 4,
            concurrent_file_download: int = 16,
            use_smart_keywords: bool = True,
            gpt_api_key: str = None
        ) -> None:
        self.embedding = HuggingFaceEmbeddings(model_name=embedding_name, model_kwargs={"device":device})
        self.web_search = SearchPipeline(
            page_timeout=page_timeout,
            file_timeout=file_timeout,
            concurrent_page=concurrent_page,
            concurrent_processor_download=concurrent_file_download,
            use_smart_keywords=use_smart_keywords,
            gpt_api_key=gpt_api_key
        )
        self.splitter = TokenTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.logger = CmdLogger("Web search")
    def __del__(self):
        del self.embedding
        del self.splitter
    async def start(self):
        await self.web_search.start()
    async def _search_to_docs(
        self, 
        query: str, 
        k_pages: int, 
        in_domain: bool, 
        engine: SearchEngineType = "brave",
        include_pdf: bool = False,
        include_image: bool = False
    ) -> list[Document]:
        self.logger.start()
        search_results = await self.web_search.call_fast(query, k_pages, in_domain, engine, include_pdf, include_image)
        self.logger.end("Web search")
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
    async def _search_to_chunks(
        self, 
        web_query: str, 
        rag_query: str, 
        k_pages: int, 
        k_chunks: int, 
        in_domain: bool, 
        engine: Literal["google", "brave"] = "brave",
        include_pdf: bool = False,
        include_image: bool = False
    ) -> tuple[list[dict], list[Document]]: 
        docs_metadata: list[dict] = []
        docs = await self._search_to_docs(web_query, k_pages, in_domain, engine, include_pdf, include_image)
        lens = []
        for doc in docs:
            doc_meta: dict = copy.deepcopy(doc.metadata) #type:ignore
            doc_meta["content"] = doc.page_content
            lens.append(len(doc.page_content))
            docs_metadata.append(doc_meta)
        chunks = self.splitter.split_documents(docs)
        vector_storage = FAISS.from_documents(chunks, self.embedding)
        self.logger.log(f"Page length: {lens}")
        self.logger.log(f"Splitted {len(docs)} docs to {len(chunks)} chunks")
        relevant_chunks = vector_storage.as_retriever(search_kwargs={"k": k_chunks}).invoke(rag_query)
        return (docs_metadata, relevant_chunks)
    async def __call__(
        self,
        web_query: str, 
        rag_query: str, 
        k_pages: int, 
        k_docs: int, 
        domain_restrict: bool, 
        engine: Literal["google", "brave"] = "brave",
        include_pdf: bool = False,
        include_image: bool = False
    ) -> tuple[list[WebSource], list[RagSource]]: 
        docs = await self._search_to_docs(web_query, k_pages, domain_restrict, engine, include_pdf, include_image)
        chunks = self.splitter.split_documents(docs)
        vector_storage = FAISS.from_documents(chunks, self.embedding)
        lens = [len(doc.page_content) for doc in docs]
        self.logger.log(f"Page length: {lens}")
        self.logger.log(f"Splitted {len(docs)} docs to {len(chunks)} chunks")
        relevant_chunks = vector_storage.as_retriever(search_kwargs={"k": k_docs}).invoke(rag_query)
        
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
            
        for chunk in relevant_chunks:
            rag_source: RagSource = {
                "url": chunk.metadata["url"],
                "title": chunk.metadata["title"],
                "text": chunk.page_content
            }
            rag_sources.append(rag_source)
            
        return web_sources, rag_sources