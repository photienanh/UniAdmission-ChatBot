from .slm import SLM
from .gemini import Gemini
from typing import Any

async def ask_llm(
    question: str,
    model_type: str,
    session_id: str,
    use_web_search=True
):
    """Hàm chung để gọi LLM - Gemini hoặc Custom LLM"""
    if "gemini" in model_type:
        result: dict[str, Any] = await  Gemini.ask(question, session_id, use_web_search)
    else:
        result: dict[str, Any] = await SLM.ask(question, session_id, use_web_search)

    return result
