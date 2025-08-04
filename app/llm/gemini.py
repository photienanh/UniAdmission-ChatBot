from .common import build_prompt, get_or_create_chat_session
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, SYSTEM_INSTRUCTION
genai.configure(api_key=GEMINI_API_KEY) #type:ignore
class Gemini:
    model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=SYSTEM_INSTRUCTION) #type:ignore
    def __init__(self) -> None:
        raise Exception(f"Static class does not support instance")
    @classmethod
    async def ask(cls, question: str, session_id: str, use_web_search: bool, max_results: int, priority_domains: bool):
        chat = get_or_create_chat_session(cls.model, session_id)
        prompt, search_sources = build_prompt(question, use_web_search, max_results)
        response = chat.send_message(prompt)

        if search_sources:
            for search_souce in search_sources: # Tempory fix
                if "description" not in search_souce:
                    search_souce["description"] = search_souce["content"][:50]
        return {
                "response": response.text,
                "sources": [],
                "search_sources": search_sources if use_web_search and search_sources else []
            }