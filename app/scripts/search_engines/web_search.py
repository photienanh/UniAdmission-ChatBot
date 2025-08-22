from langchain.text_splitter import TokenTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
import time
from langchain_core.documents import Document
from typing import Literal
import copy
import os

from .pipeline import SearchPipeline

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
    def __init__(self, embedding_name: str, chunk_size: int = 1024, chunk_overlap: int = 128) -> None:
        os.environ["WEB_SEARCH_SSL"] = str(False)
        os.environ["GOOGLE_SEARCH_API_KEY"] = "AIzaSyAtItbzZTJQijvT4A5ynzEWhY1YNXYWKNY"
        os.environ["GOOGLE_SEARCH_CX"] = "9501a956284f141ab"
        os.environ["BRAVE_SEARCH_API_KEY"] = "BSAbUIq8YC6VrPhwp688ST6Vtz7cyrH"
        self.embedding = HuggingFaceEmbeddings(model_name=embedding_name, model_kwargs={"device":"cpu"})
        self.web_search = SearchPipeline(
            page_timeout=10,
            file_timeout=10,
            concurrent_page=4,
            concurrent_processor_download=16
        )
        self.splitter = TokenTextSplitter(chunk_size=1024, chunk_overlap=128)
        self.logger = CmdLogger("Web search")
    def __del__(self):
        del self.embedding
        del self.splitter
    async def _search_to_docs(
        self, 
        query: str, 
        k_pages: int, 
        in_domain: bool, 
        engine: Literal["google", "brave"] = "brave",
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
            prefix = f"[**{search_result['title']}**]({search_result['url']}):"
            for file in search_result["pdf_content"]:
                pdf_content.append(f"{prefix}[**{file['title']}**]({file['url']}):\n{file['text']}")
            for file in search_result["image_content"]:
                image_content.append(f"{prefix}[**{file['title']}**]({file['url']}):\n{file['text']}")
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
        in_domain: bool, 
        engine: Literal["google", "brave"] = "brave",
        include_pdf: bool = False,
        include_image: bool = False
    ) -> tuple[list[dict], list[Document]]: 
        return await self._search_to_chunks(web_query, rag_query, k_pages, k_docs, in_domain, engine, include_pdf, include_image)