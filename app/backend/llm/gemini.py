import google.generativeai as genai
from google.generativeai.types import GenerationConfig
import os
from typing import AsyncGenerator

from .schema import APIJobInfo

class GeminiAPIModel:
    def __init__(self) -> None:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
    async def inference(self, info: APIJobInfo) -> AsyncGenerator[str, None]:
        params = info["sampling_params"]
        config = GenerationConfig(
            temperature=params.get("temperature", 0.8),
            top_p=params.get("top_p", 0.9),
            top_k=params.get("top_k", 16),
            max_output_tokens=params.get("max_tokens", 4096)
        )
        
        # Tạo model instance
        model = genai.GenerativeModel(info["model_id"])
        
        # Generate content với streaming (sync)
        response = model.generate_content(
            contents=info["text"],
            generation_config=config,
            stream=True
        )
        
        # Iterate through chunks synchronously trong async function
        for chunk in response:
            if hasattr(chunk, 'text') and chunk.text:
                yield chunk.text