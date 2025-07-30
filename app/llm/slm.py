import aiohttp
from fastapi import HTTPException
from backend.service_hub import direct_consume

async def post(url: str, prompt: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(url=url, data=prompt) as response:
            return await response.text()
async def direct_request(model_type: str, question: str, use_web_search: bool):
    response = await direct_consume(model_type, data={
        "question": question,
        "use_web_search": use_web_search
    })
    return response
class SLM:
    def __init__(self) -> None:
        raise Exception(f"Static class does not support instance")
    @classmethod
    async def ask(cls, model_type: str, question: str, session_id: str, use_web_search: bool):
        result: dict | None = await direct_request(model_type, question, use_web_search)
        if result != None:
            result["response"] = result["answer"]
            # print(result)
            return result
        else:
            raise HTTPException(status_code=500, detail=f"Failed to inference {model_type}")