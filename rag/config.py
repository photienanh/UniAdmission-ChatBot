"""
Configuration file for RAG system.
This file contains all configurable parameters for the RAG system.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
DATA_DIR = os.path.join(BASE_DIR, "data")
VECTOR_DB_DIR = os.path.join(BASE_DIR, "vector_db")

# Document loading and processing
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Embedding configuration
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"  # Vietnamese/multilingual support
EMBEDDING_CACHE = os.path.join(BASE_DIR, "cache", "embedding_cache")

# Retriever configuration
DEFAULT_TOP_K = 5
SIMILARITY_THRESHOLD = 0.7

# Advanced retrieval features
USE_RERANKING = False  # Bật/tắt tính năng reranking
USE_QUERY_EXPANSION = False  # Bật/tắt tính năng query expansion
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Mô hình reranker mặc định
REDUNDANT_FILTER_THRESHOLD = 0.95  # Ngưỡng lọc tài liệu trùng lặp

# LLM configuration
DEFAULT_LLM_MODEL = "meta-llama/Llama-3.2-1B" 
HUGGINGFACE_LLM_MODEL = "meta-llama/Llama-3.2-1B"  # Mô hình LLM mặc định
GOOGLE_GEMINI_MODEL = "gemini-1.5-pro-latest"  # Updated to a valid Gemini model name
OPENAI_MODEL = "gpt-3.5-turbo"  # Mô hình OpenAI mặc định

DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = None  
DYNAMIC_RESPONSE_LENGTH = True 

API_KEYS = {
    "gemini": os.getenv("GEMINI_API_KEY", "nothing"),
    "openai": os.getenv("OPENAI_API_KEY", "nothing"),
}

# RAG prompt templates
DEFAULT_RAG_PROMPT_TEMPLATE = """
Bạn là một AI tư vấn tuyển sinh đại học, dựa vào hiểu biết của mình, có thể sử dụng kèm theo những thông tin sau đây, hãy trả lời câu hỏi hoặc đưa ra tư vấn.

Thông tin được cung cấp:
{context}

Câu hỏi:
{question}

Trả lời:
"""