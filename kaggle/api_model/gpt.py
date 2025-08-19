from openai import AsyncOpenAI
import os
from typing import AsyncGenerator

from .schema import APIJobInfo

class GPTAPIModel:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))
    async def process(self, info: APIJobInfo) -> AsyncGenerator[str, None]:
        params = info["sampling_params"]
        stream = await self.client.chat.completions.create(
            model=info["model_id"], 
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý hữu ích"},
                {"role": "user", "content": info["message"]}
            ],
            max_tokens=params.get("max_tokens", 2048),
            temperature=params.get("temperature", 0.8),
            top_p=params.get("top_p", 0.9),
            stream=True
        )
        async for event in stream:
            chunk = event.choices[0].delta.content
            if chunk is not None:
                yield chunk