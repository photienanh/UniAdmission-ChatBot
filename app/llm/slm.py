import asyncio
import aiohttp
from .common import build_context, build_prompt
from config import DOMAIN, SLM_CLIENT_NAME

async def post(url: str, prompt: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(url=url, data=prompt) as response:
            return await response.text()

class SLM:
    def __init__(self) -> None:
        raise Exception(f"Static class does not support instance")
    @classmethod
    async def ask(cls, question: str, session_id: str, use_web_search: bool):
        url = f"{DOMAIN}/consume/{SLM_CLIENT_NAME}"
        # context = await build_context(question, use_web_search)
        # prompt = build_prompt(context, question)
        response = await post(url, question)
        return {
            "response": response
        }