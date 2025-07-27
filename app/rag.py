from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from rag.rag_pipeline import SimplifiedRAG
import os

_rag_instance = None

def initialize_rag():
    """Khởi tạo RAG system với embeddings và vector store"""
    global _rag_instance
    
    if _rag_instance is None:
        vector_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vector_db")
        _rag_instance = SimplifiedRAG(
            vector_db_path=vector_db_path,
            embedding_model="intfloat/multilingual-e5-small",
            llm_type="gemini",  # Default to gemini
            temperature=0.7
        )
    
    return _rag_instance.get_retriever()

def get_rag_instance():
    """Lấy instance của RAG pipeline"""
    global _rag_instance
    if _rag_instance is None:
        initialize_rag()
    return _rag_instance

def build_rag_context(question: str, retriever, k=3):
    """Truy xuất context từ RAG vector database"""
    # Truy xuất các chunk văn bản liên quan
    docs = retriever.get_relevant_documents(question, k=k)
    context = "\n\n".join([doc.page_content for doc in docs])
    return context

def ask_rag(question: str, session_id: str = None):
    """Sử dụng RAG pipeline để trả lời câu hỏi"""
    rag = get_rag_instance()
    result = rag.ask(question, session_id=session_id)
    return result

def change_llm_model(llm_type: str, model_name: str = None, temperature: float = 0.7):
    """Thay đổi mô hình LLM được sử dụng trong RAG pipeline"""
    rag = get_rag_instance()
    return rag.change_llm(llm_type, model_name, temperature)