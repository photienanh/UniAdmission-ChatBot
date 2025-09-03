from langchain_core.documents import Document
from flashrank import Ranker, RerankRequest

from ..config import PageRankerConfig, ChunkRankerConfig

class ReRanker:
    """Wrapper class for rerank page and chunks"""
    def __init__(self, page_config: PageRankerConfig, chunk_config: ChunkRankerConfig) -> None:
        self.page_config = page_config
        self.chunk_config = chunk_config
        self.logging = True
        self.ranker = Ranker(chunk_config.ranker_name, max_length=chunk_config.max_length)
    async def rerank_pages(self, docs: list[Document], query: str, relative_threshold: float = 0.5) -> list[Document]:
        """
        Perform rerank with pages.\n
        Will use llm rerank when possible, fallback to `flashrank`.
        """
        if self.page_config.use_llm and self.page_config.call is not None:
            return await self._rerank_page_llm(docs, query, relative_threshold)
        else:
            return self._rerank_page_fast_rank(docs, query, relative_threshold)
    def rerank_chunks(self, docs: list[Document], query: str, relative_threshold: float = 0.5) -> list[Document]:
        """Perform rerank with relevant chunks from vectordb search"""
        # For lookup when process result
        id_docs = {index: doc for index, doc in enumerate(docs)} 
        # Convert to flashrank format
        passages = [{
            "id": index,
            "text": chunk.page_content
        } for index, chunk in enumerate(docs)]
        request = RerankRequest(query=query, passages=passages)
        results = self.ranker.rerank(request)
        max_score = 0
        for result in results:
            max_score = max(max_score, result["score"])
        score_threshold = 0 if max_score == 0 else max_score * relative_threshold
        
        valid_chunks: list[Document] = []
        for result in results:
            if result["score"] >= score_threshold:
                valid_chunks.append(id_docs[result["id"]])
        if not self.chunk_config.keep_order:
            return valid_chunks
        else:
            return sorted(valid_chunks, key=lambda x: (x.metadata["page_index"], x.metadata["chunk_index"]))
    async def _rerank_page_llm(self, docs: list[Document], query: str, relative_threshold: float = 0.5) -> list[Document]:
        """Perform LLM rerank with page `Document`. Change page index inside it, old page index still keep as `old_page_idex` field."""
        if self.page_config.call is None: raise ValueError("Page Reranker call is None")
        # For lookup when process result
        id_docs = {index: doc for index, doc in enumerate(docs)} 
        if self.logging:
            print("---Original order ---")
            for doc in docs:
                print(doc.metadata["title"])
        inputs = [(str(doc.metadata["title"]), str(doc.metadata["description"])) for doc in docs]
        scores = await self.page_config.call(query, inputs) 
        
        max_score = 0
        for score in scores:
            max_score = max(max_score, score)
        score_threshold = 0 if max_score == 0 else max_score * relative_threshold
        
        reorder_docs: list[Document] = []
        for index, score in enumerate(scores):
            if score >= score_threshold:
                doc = id_docs[index]
                doc.metadata["old_page_index"] = doc.metadata["page_index"]
                doc.metadata["confidence"] = score
                reorder_docs.append(doc)
        reorder_docs = sorted(reorder_docs, key=lambda x: x.metadata["confidence"], reverse=True)
        for index, doc in enumerate(reorder_docs):
            doc.metadata["page_index"] = index
        if self.logging:
            print("---Reorder ---")
            for doc in reorder_docs:
                print(f'{doc.metadata["confidence"]:.5f}', doc.metadata["title"])
                print(doc.metadata["description"])
        return reorder_docs
    def _rerank_page_fast_rank(self, docs: list[Document], query: str, relative_threshold: float = 0.5) -> list[Document]:
        """Perform FlashRank rerank with pages. Change page index inside it, old page index still keep as `old_page_idex` field."""
        # For lookup when process result
        id_pages = {index: doc for index, doc in enumerate(docs)} 
        # Convert to flashrank format
        if self.logging:
            print("---Original order ---")
            for doc in docs:
                print(doc.metadata["title"])
            passages = [{
                "id": index,
                "text": f'{page.metadata["title"]}:\n {page.metadata["description"]}',
            } for index, page in enumerate(docs)]
        request = RerankRequest(query=query, passages=passages)
        results = self.ranker.rerank(request)
        
        max_score = 0
        for result in results:
            max_score = max(max_score, result["score"])
        score_threshold = 0 if max_score == 0 else max_score * relative_threshold
        
        reorder_docs: list[Document] = []
        for index, result in enumerate(results):
            if result["score"] >= score_threshold:
                page = id_pages[result["id"]]
                page.metadata["old_page_index"] = page.metadata["page_index"]
                page.metadata["page_index"] = index
                page.metadata["confidence"] = result["score"]
                reorder_docs.append(page)
            
        print("---Reorder ---")
        for doc in reorder_docs:
            print(f'{doc.metadata["confidence"]:.5f}', doc.metadata["title"])
            print(doc.metadata["description"])
        return reorder_docs