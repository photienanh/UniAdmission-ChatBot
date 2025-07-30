from .common import build_prompt, get_or_create_chat_session
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, SYSTEM_INSTRUCTION
genai.configure(api_key=GEMINI_API_KEY) #type:ignore
class Gemini:
    model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=SYSTEM_INSTRUCTION) #type:ignore
    def __init__(self) -> None:
        raise Exception(f"Static class does not support instance")
    @classmethod
    async def ask(cls, question: str, session_id: str, use_web_search: bool):
        chat = get_or_create_chat_session(cls.model, session_id)
        prompt, search_sources = build_prompt(question, use_web_search, max_results=3)
        response = chat.send_message(prompt)
  # source : {1: {"url": "https://example.com", 
    #               "title": "Example Title", 
    #               "content": "Example content"},
    #         2: {"url": "https://example2.com",
    #               "title": "Example Title 2", 
    #               "content": "Example content 2"},
    #         3: {"url": "https://example3.com",
    #               "title": "Example Title 3", 
    #               "content": "Example content 3"}}
        # if not use_web_search:
        #     return {
        #         "response": response.text
        #     }
        # if source is None:
        #     return {
        #         "response": response.text
        #     }
                
        return {
                "response": response.text,
                "context": "example context" if use_web_search else "",
                "sources": [],
                "search_sources": search_sources if use_web_search and search_sources else []
            }