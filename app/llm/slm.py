from backend.model_hub import inference
from backend.schema import WebSearchParam, ModelOutput, ModelInput, UserMessage, BotMessage

class SLM:
    def __init__(self) -> None:
        raise Exception(f"Static class does not support instance")
    @classmethod
    async def ask(cls, 
            model_id: str, 
            question: str, 
            session_id: str,
            web_search: WebSearchParam | None
    ) -> ModelOutput:
        # Todo: Get history
        input: ModelInput = {
            "context": [
                {
                    "role": "user",
                    "message": question
                }
            ],
            "model_id": model_id,
            "web_search": web_search
        }
        output = await inference(input)
        return output