from .web_search import get_source

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
        source = get_source(question, max_results)
        if source is None:
            return f"""Câu hỏi: {question}""", None
        context = ""
        for s in source.values():
            context += f"Nguồn: {s['url']}" + "\n\n" + s['content'] + 100*'-' + "\n\n"
        prompt = f"""
Thông tin tham khảo:
{context}
Câu hỏi: {question}
"""
        return prompt, source
    else:
        return f"""Câu hỏi: {question}""", None
