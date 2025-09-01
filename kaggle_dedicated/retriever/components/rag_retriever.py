from langchain_huggingface import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever as LangChainBM25Retriever
from langchain_core.documents import Document
from ..config import RagConfig

class FaissRetriever:
    """Sentence Transformer based RAG retriever"""
    def __init__(self, config: RagConfig) -> None:
        self.embedding = HuggingFaceEmbeddings(model_name=config.embedding_name, model_kwargs={"device":config.device})
    def __call__(self, docs: list[Document], query: str, k: int) -> list[Document]:
        """Perform Sentence Transformer rag search, return a list of relevant documents"""
        vector_storage = FAISS.from_documents(docs, self.embedding)
        relevant_chunks = vector_storage.as_retriever(search_kwargs={"k": k}).invoke(query)
        return relevant_chunks

class BM25Retriever:
    """BM25 based RAG retriever"""
    def __init__(self, config: RagConfig) -> None:
        pass
    def __call__(self, docs: list[Document], query: str, k: int) -> list[Document]:
        """Perform BM25 rag searh, return a list of relevant documents"""
        retriever = LangChainBM25Retriever.from_documents(docs)
        retriever.k = k
        relevant_chunks = retriever.invoke(query)
        return relevant_chunks