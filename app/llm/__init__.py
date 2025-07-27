from .slm import SLM
from .gemini import Gemini

def initialize_llm():
    from .rag import RAG
    RAG.initialize()

async def ask_llm(
    question: str,
    session_id: str,
    use_custom_llm=False,
    use_web_search=True
):
    """Hàm chung để gọi LLM - Gemini hoặc Custom LLM"""
    if use_custom_llm:
        return await SLM.ask(question, session_id, use_web_search)
    else:
        return await Gemini.ask(question, session_id, use_web_search)
