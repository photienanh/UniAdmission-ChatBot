from .web_search import get_source
from datetime import datetime, timezone
chat_sessions = {}

def get_or_create_chat_session(model, session_id):
    """Lấy hoặc tạo chat session cho session_id"""
    if session_id not in chat_sessions:
        chat_sessions[session_id] = model.start_chat()
    return chat_sessions[session_id]

def clear_chat_session(session_id):
    """Xóa chat session khỏi memory"""
    if session_id in chat_sessions:
        del chat_sessions[session_id]

def build_prompt(question, use_web_search, max_results):
    """Tạo prompt với context và question"""
    if use_web_search:
        search_sources = get_source(question, max_results)
        if search_sources is None:
            return f"""Câu hỏi: {question}""", None
        for s in search_sources:
            s["timestamp"] = datetime.now(timezone.utc).isoformat()
        context = ""
        for source in search_sources:
            context += f"{source['content']}\n\n" + 100 * '-' + "\n\n"
        prompt = f"""
Thông tin tham khảo:
{context}
Câu hỏi: {question}
"""
        return prompt, search_sources
    else:
        return f"""Câu hỏi: {question}""", None
