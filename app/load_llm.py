from dotenv import load_dotenv
import os
import google.generativeai as genai
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import sys
import os

# Add the parent directory to sys.path to allow importing from the rag package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag import rag_pipeline

from rag.rag_pipeline import SimplifiedRAG

# Khởi tạo là None thay vì tạo instance mới mỗi lần import
rag_pipeline = None

def initialize_llm(llm_type: str = 'openai'):
    global rag_pipeline
    if rag_pipeline is None:
        # Khởi tạo rag_pipeline nếu chưa được khởi tạo
        rag_pipeline = SimplifiedRAG()
    try:
        return rag_pipeline.change_llm(llm_type.lower())
    except ValueError as e:
        print(f"Error initializing LLM: {e}")
        return None

def create_rag_pipeline(vector_db_path: str = None, embedding_model: str = "intfloat/multilingual-e5-small", llm_type: str = "huggingface", llm_model_name: str = None, temperature: float = 0.7, top_k: int = 3):
    global rag_pipeline
    # Cập nhật biến toàn cục thay vì chỉ trả về một phiên bản mới
    rag_pipeline = SimplifiedRAG(
        vector_db_path=vector_db_path,
        embedding_model=embedding_model,
        llm_type=llm_type,
        llm_model_name=llm_model_name,
        temperature=temperature,
        top_k=top_k
    )
    return rag_pipeline

def ask(question: str):
    global rag_pipeline
    try:
        if rag_pipeline is None:
            # Tự động khởi tạo nếu chưa được khởi tạo
            rag_pipeline = SimplifiedRAG()
            print("Automatically initialized RAG pipeline with default settings.")
        
        result = rag_pipeline.ask(question)
        
        ans = result.get('answer', 'No answer found.')
        if "Trả lời:" in ans:
            ans = ans.split("Trả lời:", 1)[1].strip()
            
        return {
            'response': ans,
            'sources': [doc.page_content for doc in result.get('source_documents', [])]
        }
    
    except Exception as e:
        print(f"Error in ask function: {e}")
        return {
            'response': f"Sorry, an error occurred: {str(e)}",
            'sources': []
        }