from google import genai
from google.genai.types import GenerateContentConfig
import os
from .schema import APIJobInfo, APIJobResult

class GeminiAPIModel:
    def __init__(self) -> None:
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    async def process(self, info: APIJobInfo) -> APIJobResult:
        params = info["sampling_params"]
        config = GenerateContentConfig(
            temperature=params.get("temperature", 0.8),
            top_p=params.get("top_p", 0.9),
            top_k=params.get("top_k", 16),
            max_output_tokens=params.get("max_tokens", 4096)
        )
        response = self.client.models.generate_content(
            model=info["model_id"],
            contents=info["message"],
            config=config
        )
        result: APIJobResult = {
            "text": [response.text or ""]
        }
        return result