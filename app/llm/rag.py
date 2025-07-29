from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever
import asyncio
from concurrent.futures import ThreadPoolExecutor
def initialize_rag():
    """Khởi tạo RAG system với embeddings và vector store"""
    embedding = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-small", cache_folder='./cache')
    vectorstore = Chroma(persist_directory="../vector_db", embedding_function=embedding)
    retriever = vectorstore.as_retriever()
    return retriever
class RAG:
    retriever: VectorStoreRetriever
    # executor = ThreadPoolExecutor(1)
    def __init__(self) -> None:
        raise Exception(f"Static class does not support instance")
    @classmethod
    def __setup(cls):
        # RAG.retriever = initialize_rag()
        pass
    @classmethod
    def initialize(cls):
        # if not hasattr(RAG, "retriever"):
            # future = cls.executor.submit(cls.__setup) # Move retriever to executor thread
            # future.result()
        pass
    @classmethod
    def __invoke(cls, question: str, k: int = 3):
        return cls.retriever.invoke(question, k=k)
    @classmethod
    async def build_rag_context(cls, question: str, k: int = 3):
        """Truy xuất context từ RAG vector database"""
        loop = asyncio.get_running_loop()
        # Truy xuất các chunk văn bản liên quan
        # docs = await loop.run_in_executor(
        #     cls.executor, 
        #     cls.__invoke,
        #     question, k
        # )
        docs = []
        context = "\n\n".join([doc.page_content for doc in docs])
        return context