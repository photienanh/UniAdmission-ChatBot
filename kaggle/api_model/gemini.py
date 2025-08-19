from google import genai
from google.genai.types import GenerateContentConfig
import os
from typing import AsyncGenerator

from .schema import APIJobInfo

class GeminiAPIModel:
    def __init__(self) -> None:
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    async def process(self, info: APIJobInfo) -> AsyncGenerator[str, None]:
        params = info["sampling_params"]
        config = GenerateContentConfig(
            temperature=params.get("temperature", 0.8),
            top_p=params.get("top_p", 0.9),
            top_k=params.get("top_k", 16),
            max_output_tokens=params.get("max_tokens", 2048)
        )
        stream = await self.client.aio.models.generate_content_stream(
            model=info["model_id"],
            contents=info["message"],
            config=config,
        )
        async for chunk in stream:
            text = chunk.text
            if text != None:
                yield text