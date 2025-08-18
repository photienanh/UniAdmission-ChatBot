from typing import AsyncGenerator, Callable, Awaitable, TypedDict, Optional

from core.types import ModelInfo, GenerationParams, ModelPreOutput
from config import GEMINI_MODEL

from .schema import APIJobInfo
from .gemini import GeminiAPIModel
from .utils import generate_id
from .kaggle import KaggleManager

class JobInfo(TypedDict):
    finish_call: Callable[[str], Awaitable]
    domain: str
    id: str
    server_kwargs: Optional[dict]

class ModelManager:
    _gemini_api = GeminiAPIModel()
    _jobs: dict[str, JobInfo] = {} # No timeout implemented yet
    @classmethod
    async def inference(cls, job_id: str) -> AsyncGenerator[str, None]:
        job_info = cls._jobs.pop(job_id)
        if job_info["server_kwargs"]:
            kwargs = job_info["server_kwargs"]
            params: GenerationParams = kwargs["generation_params"]
            model_id: str = kwargs["model_id"]
            text: str = kwargs["text"]
            api_job_info: APIJobInfo = {
                "model_id": model_id,
                "sampling_params": params,
                "text": text
            }
            total = ""
            async for chunk in cls._gemini_api.inference(api_job_info):
                total += chunk
                yield chunk
            await job_info["finish_call"](total)
        else:
            total = ""
            async for chunk in KaggleManager.inference(job_info["domain"], job_id):
                total += chunk
                yield chunk
            await job_info["finish_call"](total)
    @classmethod
    async def pre_inference(cls, text: str, model_id: str, params: GenerationParams, finish_call: Callable[[str], Awaitable]) -> ModelPreOutput | None:
        job_id = generate_id()
        server_kwargs: dict | None = None
        if model_id.startswith("api:"):
            pre_output: ModelPreOutput | None = {
                "stream_id": job_id,
                "model_id": model_id,
                "generation_params": params,
                "web_sources": [],
                "rag_sources": [],
                "extra_data": {}
            }
            domain = ""
            server_kwargs = {
                "model_id": GEMINI_MODEL,
                "text": text,
                "generation_params": params
            }
        else:
            pack = await KaggleManager.pre_inference(job_id, text, model_id, params)
            if pack != None:
                domain, pre_output = pack
            else:
                return None
        job_info: JobInfo = {
            "domain": domain,
            "finish_call": finish_call,
            "id": job_id,
            "server_kwargs": server_kwargs
        }
        cls._jobs[job_id] = job_info
        return pre_output
    @classmethod
    def get_models(cls) -> list[ModelInfo]:
        result: list[ModelInfo] = [
            {
                "name": "Gemini (Server)",
                "id": f"api:{GEMINI_MODEL}",
                "streaming": False,
                "source": "server"
            }
        ]
        result.extend(KaggleManager.get_models())
        return result