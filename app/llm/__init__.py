from .slm import SLM
from .gemini import Gemini
from typing import Any
from config import GEMINI_MODEL

async def ask_llm(
    question: str,
    model_id: str,
    session_id: str,
    web_search_params: Any | None
):
    """Hàm chung để gọi LLM - Gemini hoặc Custom LLM"""
    if model_id == GEMINI_MODEL:
        result: dict[str, Any] = await  Gemini.ask(question, session_id, web_search_params)
    else:
        # result: dict[str, Any] = await SLM.ask_old(model_type ,question, session_id, use_web_search)
        intermediate = await SLM.ask(model_id, question, session_id, web_search={"in_domain": False, "k_docs": 3, "k_pages": 3})
        result = {
            "message": intermediate["response"]["message"],
            "sources": intermediate["response"]["search_sources"],
            "search_sources": intermediate["response"]["search_sources"]
        }
    return result