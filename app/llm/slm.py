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
            search_sources: list = result.get("search_sources", []) #type:ignore
            for search_souce in search_sources: # Tempory fix
                if "description" not in search_souce:
                    search_souce["description"] = search_souce["content"][:50]
            sources: list = result.get("sources", [])
            for source in sources:
                if "description" not in source:
                    source["description"] = source["content"][:50]
            # print(result)
            return result
        else:
            raise HTTPException(status_code=500, detail=f"Failed to inference {model_type}")