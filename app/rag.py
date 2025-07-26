from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def initialize_rag():
    """Khởi tạo RAG system với embeddings và vector store"""
    embedding = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-small", cache_folder='./cache')
    vectorstore = Chroma(persist_directory="../vector_db", embedding_function=embedding)
    retriever = vectorstore.as_retriever()
    return retriever

def build_rag_context(question: str, retriever, k=3):
    """Truy xuất context từ RAG vector database"""
    # Truy xuất các chunk văn bản liên quan
    docs = retriever.invoke(question, k=k)
    context = "\n\n".join([doc.page_content for doc in docs])
    return context