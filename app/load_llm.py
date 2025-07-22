from dotenv import load_dotenv
import os
import google.generativeai as genai
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import requests

# Dictionary để lưu trữ chat sessions cho mỗi session_id
chat_sessions = {}

def get_custom_llm_url():
    """Đọc URL từ file link.txt"""
    with open('link.txt', 'r') as f:
        url = f.read().strip()
        url = "https://" + url + ".ngrok-free.app/generate"
        return url

def initialize_rag():
    embedding = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-small", cache_folder='./cache')
    vectorstore = Chroma(persist_directory="../vector_db", embedding_function=embedding)
    retriever = vectorstore.as_retriever()
    return retriever

def build_rag_context(question: str, retriever, k=3):
    # Truy xuất các chunk văn bản liên quan
    docs = retriever.invoke(question, k=k)
    context = "\n\n".join([doc.page_content for doc in docs])
    return context

def initialize_llm():
    load_dotenv('gemini_api_key.env')
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(
        "gemini-2.0-flash-lite-preview-02-05",
        system_instruction="Bạn là một AI tư vấn tuyển sinh đại học chuyên nghiệp. Hãy trả lời các câu hỏi một cách chính xác, hữu ích và thân thiện. Có thể sử dụng những thông tin được cung cấp để đưa ra câu trả lời hoặc lời khuyên tốt nhất."
    )
    return model

def get_or_create_chat_session(model, session_id):
    """Lấy hoặc tạo chat session cho session_id"""
    if session_id not in chat_sessions:
        chat_sessions[session_id] = model.start_chat()
    return chat_sessions[session_id]

def ask_custom_llm(question):
    url = get_custom_llm_url()
    payload = {"prompt": question}
    response = requests.post(url, json=payload)
    return {"response": response.json()["response"]}  # Trả về dictionary với key "response"


def ask_gemini_with_chat(question, model, retriever, session_id):
    """Hỏi Gemini với conversation memory sử dụng start_chat"""
    try:
        # Lấy chat session
        chat = get_or_create_chat_session(model, session_id)
        
        # Lấy thông tin RAG context
        rag_context = build_rag_context(question, retriever)
        
        # Tạo message với RAG context
        message_with_context = f"""
Thông tin tham khảo:
{rag_context}

Câu hỏi: {question}
"""
        
        # Gửi message và nhận response
        response = chat.send_message(message_with_context)
        
        return {"response": response.text}
        
    except Exception as e:
        return {"response": f"Xin lỗi, có lỗi xảy ra: {str(e)}"}

def ask_llm(question, model, retriever, session_id=None, use_custom_llm=False):
    """Hàm chung để gọi LLM - Gemini hoặc Custom LLM"""
    if use_custom_llm:
        # Sử dụng API LLM tự phát triển (không có conversation memory)
        return ask_custom_llm(question)
    else:
        # Sử dụng Gemini với conversation memory
        return ask_gemini_with_chat(question, model, retriever, session_id)

def clear_chat_session(session_id):
    """Xóa chat session khỏi memory"""
    if session_id in chat_sessions:
        del chat_sessions[session_id]

# Giữ lại hàm cũ để tương thích ngược
# def ask_gemini(question, model, retriever):
#     prompt = f"""
# Bạn là một AI tư vấn tuyển sinh đại học, dựa vào hiểu biết của mình, có thể sử dụng kèm theo những thông tin sau đây, hãy trả lời câu hỏi hoặc đưa ra tư vấn.

# Thông tin được cung cấp:
# {build_rag_context(question, retriever)}

# Câu hỏi:
# {question}

# Trả lời:
# """
#     response = model.generate_content(prompt)
#     return {"response": response.text}