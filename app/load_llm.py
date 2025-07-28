import google.generativeai as genai
import requests
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
        system_instruction="Bạn là một AI tư vấn tuyển sinh đại học chuyên nghiệp. Hãy trả lời các câu hỏi một cách chính xác, hữu ích và thân thiện. Có thể sử dụng những thông tin được cung cấp để đưa ra câu trả lời hoặc lời khuyên tốt nhất. Nếu được cung cấp link nguồn thì thêm vào phần cuối câu trả lời, nếu không được cung cấp thì không thêm.",
    )
    return model

def get_or_create_chat_session(model, session_id):
    """Lấy hoặc tạo chat session cho session_id"""
    if session_id not in chat_sessions:
        chat_sessions[session_id] = model.start_chat()
    return chat_sessions[session_id]

def build_prompt(question, use_web_search):
    """Tạo prompt với context và question"""
    if use_web_search:
        context = build_web_search_context(question)
        return f"""
Thông tin tham khảo:
{context}

Câu hỏi: {question}
"""
    else:
        return f"""Câu hỏi: {question}"""

def ask_custom_llm(question, use_web_search):
    """Gọi API LLM tự phát triển với RAG context"""
    try:
        # Tạo prompt với context cho custom model
        prompt = build_prompt(question, use_web_search)
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


def ask_gemini(question, gemini, session_id, use_web_search):
    """Hỏi Gemini với conversation memory sử dụng start_chat"""
    try:
        # Lấy chat session
        chat = get_or_create_chat_session(gemini, session_id)
        
        # Tạo message với context
        prompt = build_prompt(question, use_web_search)
        # Gửi message và nhận response
        response = chat.send_message(prompt)
        
        return {"response": response.text}
        
    except Exception as e:
        return {"response": f"Xin lỗi, có lỗi xảy ra: {str(e)}"}

def ask_llm(question, gemini, session_id=None, use_gemini=True, use_web_search=False):
    """Hàm chung để gọi LLM - Gemini hoặc Custom LLM"""
    if use_gemini:
        return ask_gemini(question, gemini, session_id, use_web_search)
    else:
        return ask_custom_llm(question, use_web_search)

def clear_chat_session(session_id):
    """Xóa chat session khỏi memory"""
    if session_id in chat_sessions:
        del chat_sessions[session_id]
