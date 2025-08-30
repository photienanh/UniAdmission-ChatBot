from typing import AsyncGenerator, Callable, Awaitable, TypedDict, Optional

from core.types import ModelInfo, GenerationParams, ModelPreOutput
from config import GEMINI_MODEL

from ..cache.history_cache import get_history
from .utils import load_history_from_db
from .schema import APIJobInfo
from .gemini import GeminiAPIModel
from .utils import generate_id
from .kaggle import KaggleManager

class JobInfo(TypedDict):
    finish_call: Callable[[str, list], Awaitable]  # Updated to accept web_sources
    domain: str
    id: str
    server_kwargs: Optional[dict]

class ModelManager:
    _gemini_api = GeminiAPIModel()
    _jobs: dict[str, JobInfo] = {} # No timeout implemented yet
            
    @classmethod
    async def pre_inference(cls, question: str, model_id: str, params: GenerationParams, finish_call: Callable[[str], Awaitable], session_id: Optional[str] = None) -> ModelPreOutput | None:
        job_id = generate_id()
        server_kwargs: dict | None = None
        if model_id.startswith("api:"):
            # Get web search params and pre-compute sources for pre_output
            k_pages = params.get("k_pages", 0)
            domain_restrict = params.get("domain_restrict", False)
            
            # Pre-compute web sources to include in response
            try:
                prompt, web_sources = cls._gemini_api.build_prompt(question, k_pages, domain_restrict)
            except Exception as e:
                web_sources = None
            
            pre_output: ModelPreOutput | None = {
                "stream_id": job_id,
                "model_id": model_id,
                "generation_params": params,
                "web_sources": web_sources,
                "rag_sources": [],
                "extra_data": {}
            }
            domain = ""
            server_kwargs = {
                "model_id": GEMINI_MODEL,
                "text": question,
                "prompt": prompt,
                "generation_params": params,
                "session_id": session_id,  # Add session_id,
                "web_sources": web_sources  # Cache web sources to avoid duplicate search
            }
        else:
            # If we have a session_id, try to include past messages as history
            history = None
            if session_id:
                try:
                    msgs = await get_history(session_id, loader=load_history_from_db)
                    history = [
                        {"role": ("assistant" if m.role == "bot" else "user"), "content": m.text}
                        for m in msgs
                    ]
                except Exception:
                    history = None
                    
            pack = await KaggleManager.pre_inference(job_id, question, model_id, params, history)
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
    async def inference(cls, job_id: str) -> AsyncGenerator[str, None]:
        job_info = cls._jobs.pop(job_id)
        if job_info["server_kwargs"]:
            kwargs = job_info["server_kwargs"]
            params: GenerationParams = kwargs["generation_params"]
            model_id: str = kwargs["model_id"]
            
            conversation_history = []
            session_id = kwargs.get("session_id")
            if session_id:
                try:
                    msgs = await get_history(session_id, loader=load_history_from_db)
                    for m in msgs:
                        if m.role == "user":
                            conversation_history.append({"role": "user", "parts": [{"text": m.text}]})
                        else:
                            conversation_history.append({"role": "model", "parts": [{"text": m.text}]})
                except Exception:
                    pass
            
            user_message = kwargs["prompt"]
            conversation_history.append({"role": "user", "parts": [{"text": user_message}]})
            print("Conversation History:", conversation_history)

            api_job_info = APIJobInfo(
                model_id=model_id,
                conversation=conversation_history,
                sampling_params=params,
                web_sources=kwargs.get("web_sources"),
                session_id=kwargs.get("session_id")
            )

            total = ""
            async for chunk in cls._gemini_api.inference(api_job_info):
                total += chunk
                yield chunk
            
            # Lấy web_sources từ api_job_info sau khi inference
            web_sources = api_job_info.get("web_sources", [])
            await job_info["finish_call"](total, web_sources)
        else:
            total = ""
            job_info_id = job_info["id"]
            async for chunk in KaggleManager.inference(job_info["domain"], job_id):
                total += chunk
                yield chunk
            
            # Get stored sources from KaggleManager
            web_sources, rag_sources = KaggleManager.get_stored_sources(job_info_id)
            # Combine web_sources and rag_sources into one list for compatibility
            all_sources = web_sources + rag_sources
            await job_info["finish_call"](total, all_sources)
            
    @classmethod
    async def get_models(cls) -> list[ModelInfo]:
        result: list[ModelInfo] = [
            {
                "name": "Gemini (Server)",
                "id": f"api:{GEMINI_MODEL}",
                "streaming": False,
                "source": "server"
            }
        ]
        result.extend(await KaggleManager.get_models())
        return result