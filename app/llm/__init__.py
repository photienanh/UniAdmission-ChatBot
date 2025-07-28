from .slm import SLM
from .gemini import Gemini
from typing import Any

def initialize_llm():
    from .rag import RAG
    RAG.initialize()

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
    result["response"] =  f"Using: {model_type}\n{result["response"]}"
    result["sources"] = [
        {
            "url": "example.com",
            "content": "exmaplete"
        },
        {
            "url": "example2.com",
            "content": "hmmm"
        }

    ]
    return result
