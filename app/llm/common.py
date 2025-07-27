from .rag import RAG
def build_prompt(context: str, question: str):
    """Tạo prompt với context và question"""
    return f"Thông tin tham khảo:\n{context}\nCâu hỏi: {question}"

async def build_context(question: str, use_web_search: bool):
    """Xây dựng context cho câu hỏi, có thể sử dụng RAG hoặc web search"""
    if use_web_search:
        return "Not implemented"
    else:
        return await RAG.build_rag_context(question)