from langchain_huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever as LangChainBM25Retriever
from ..schema import RagSource
from ..config import RagConfig
from .converter import RagSourceToDocumentConverter

# This and Splitter Module is only parts that use langchain

class FaissRetriever:
    """Sentence Transformer based RAG retriever"""
    def __init__(self, config: RagConfig) -> None:
        self.config = config
        self.converter = RagSourceToDocumentConverter()
        self.embedding = HuggingFaceEmbeddings(model_name=config.embedding_name, model_kwargs={"device":config.device})
    def retrieve(self, sources: list[RagSource], query: str, k: int) -> list[RagSource]:
        """Perform Sentence Transformer rag search, return a list of relevant sources"""
        docs = [self.converter.convert(source) for source in sources]
        vector_storage = FAISS.from_documents(docs, self.embedding)
        relevant_chunks = vector_storage.as_retriever(search_kwargs={"k": k}).invoke(query)
        results = [self.converter.revert(chunk) for chunk in relevant_chunks]
        if self.config.keep_order:
            results = sorted(results, key=lambda source: source["chunk_index"])
        return results
class BM25Retriever:
    """BM25 based RAG retriever"""
    def __init__(self, config: RagConfig) -> None:
        self.config = config
        self.converter = RagSourceToDocumentConverter()
    def retrieve(self, sources: list[RagSource], query: str, k: int) -> list[RagSource]:
        """Perform BM25 rag searh, return a list of relevant sources"""
        docs = [self.converter.convert(source) for source in sources]
        retriever = LangChainBM25Retriever.from_documents(docs)
        retriever.k = k
        relevant_chunks = retriever.invoke(query)
        results = [self.converter.revert(chunk) for chunk in relevant_chunks]
        if self.config.keep_order:
            results = sorted(sources, key=lambda source: source["chunk_index"])
        return results
