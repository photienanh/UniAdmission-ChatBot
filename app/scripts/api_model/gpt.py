from openai import OpenAI
import os
from .schema import APIJobInfo, APIJobResult

class GPTAPIModel:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))
    async def process(self, info: APIJobInfo) -> APIJobResult:
        params = info["sampling_params"]
        response = self.client.chat.completions.create(
            model=info["model_id"], 
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý hữu ích"},
                {"role": "user", "content": info["message"]}
            ],
            max_tokens=params.get("max_tokens", 4096),
            temperature=params.get("temperature", 0.8),
            top_p=params.get("top_p", 0.9)
        )
        result: APIJobResult = {
            "text": [response.choices[0].message.content or ""],
        }
        return result