from .common import build_context, build_prompt
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, SYSTEM_INSTRUCTION
genai.configure(api_key=GEMINI_API_KEY)
class Gemini:
    model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=SYSTEM_INSTRUCTION) #type:ignore
    def __init__(self) -> None:
        raise Exception(f"Static class does not support instance")
    @classmethod
    async def ask(cls, question: str, session_id: str, use_web_search: bool):
        context = await build_context(question, use_web_search)
        prompt = build_prompt(context, question)
        session = cls.model.start_chat()
        response = await session.send_message_async(prompt)
        return {
            "response": response.text
        }