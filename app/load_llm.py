import google.generativeai as genai
import requests
from rag import build_rag_context
from web_search import build_web_search_context, get_api_key

# Dictionary để lưu trữ chat sessions cho mỗi session_id
chat_sessions = {}

def get_custom_llm_url():
    """Đọc URL từ file link.txt"""
    with open('link.txt', 'r') as f:
        url = f.read().strip()
        url = "https://" + url + ".ngrok-free.app/generate"
        return url

def initialize_gemini():
    GEMINI_API_KEY = get_api_key()["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        "gemini-2.0-flash-lite-preview-02-05",
        system_instruction="Bạn là một AI tư vấn tuyển sinh đại học chuyên nghiệp. Hãy trả lời các câu hỏi một cách chính xác, hữu ích và thân thiện. Có thể sử dụng những thông tin được cung cấp để đưa ra câu trả lời hoặc lời khuyên tốt nhất. Nếu được cung cấp link nguồn thì thêm vào phần cuối câu trả lời.",
    )
    return model

def get_or_create_chat_session(model, session_id):
    """Lấy hoặc tạo chat session cho session_id"""
    if session_id not in chat_sessions:
        chat_sessions[session_id] = model.start_chat()
    return chat_sessions[session_id]

def build_context(question, retriever, use_web_search=True):
    """Xây dựng context cho câu hỏi, có thể sử dụng RAG hoặc web search"""
    if use_web_search:
        # Sử dụng web search để lấy context
        return build_web_search_context(question)
    else:
        # Sử dụng RAG để lấy context
        return build_rag_context(question, retriever)

def build_prompt(context, question):
    """Tạo prompt với context và question"""
    return f"""
Thông tin tham khảo:
{context}

Câu hỏi: {question}
"""

def ask_custom_llm(question, retriever, use_web_search=True):
    """Gọi API LLM tự phát triển với RAG context"""
    try:
        # Lấy thông tin context dựa trên lựa chọn
        context = build_context(question, retriever, use_web_search)
        
        # Tạo prompt với context cho custom model
        prompt = build_prompt(context, question)
        url = get_custom_llm_url()
        
        payload = {"prompt": prompt.strip()}
        
        # Thêm headers
        headers = {
            'Content-Type': 'application/json',
            'ngrok-skip-browser-warning': 'true'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            return {"response": result["response"]}
        else:
            error_msg = f"Lỗi API: {response.status_code} - {response.text[:100]}"
            return {"response": error_msg}
            
    except requests.exceptions.Timeout:
        error_msg = "API phản hồi quá chậm. Vui lòng thử lại."
        return {"response": error_msg}
    except requests.exceptions.ConnectionError:
        error_msg = "Không thể kết nối đến API. Kiểm tra lại kết nối."
        return {"response": error_msg}
    except Exception as e:
        error_msg = f"Lỗi: {str(e)}"
        return {"response": error_msg}


def ask_gemini(question, model, retriever, session_id, use_web_search=True):
    """Hỏi Gemini với conversation memory sử dụng start_chat"""
    try:
        # Lấy chat session
        chat = get_or_create_chat_session(model, session_id)
        
        # Lấy thông tin context dựa trên lựa chọn
        context = build_context(question, retriever, use_web_search)
        
        # Tạo message với context
        prompt = build_prompt(context, question)
        # Gửi message và nhận response
        response = chat.send_message(prompt)
        
        return {"response": response.text}
        
    except Exception as e:
        return {"response": f"Xin lỗi, có lỗi xảy ra: {str(e)}"}

def ask_llm(question, model, retriever, session_id=None, use_gemini=True, use_web_search=True):
    """Hàm chung để gọi LLM - Gemini hoặc Custom LLM"""
    if use_gemini:
        return ask_gemini(question, model, retriever, session_id, use_web_search)
    else:
        return ask_custom_llm(question, retriever, use_web_search)

def clear_chat_session(session_id):
    """Xóa chat session khỏi memory"""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
