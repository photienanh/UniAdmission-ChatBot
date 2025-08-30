# from typing import AsyncGenerator, Callable, Awaitable, TypedDict, Optional
# from datetime import datetime, timezone

# from core.types import ModelInfo, GenerationParams, ModelPreOutput, ModelOutput
# from config import GEMINI_MODEL
# from database import add_conversation

# from .history_cache import get_history, Msg
# from .utils import load_history_from_db
# from .schema import APIJobInfo
# from .gemini import GeminiAPIModel
# from .utils import generate_id
# from .kaggle import KaggleManager

# class JobInfo(TypedDict):
#     domain: str
#     id: str
#     kwargs: dict # Store server info or kaggle request info

# class ModelManager:
#     _gemini_api = GeminiAPIModel()
#     _jobs: dict[str, JobInfo] = {} # No timeout implemented yet
#     @classmethod
#     async def inference(cls, job_id: str) -> AsyncGenerator[str, None] | str:
#         """Return text generator or redirect url"""
#         job_info = cls._jobs.pop(job_id)
        
#         if job_info["server_kwargs"]:
#             kwargs = job_info["server_kwargs"]
#             params: GenerationParams = kwargs["generation_params"]
#             model_id: str = kwargs["model_id"]
#             text: str = kwargs["text"]
            
#             api_job_info: APIJobInfo = {
#                 "model_id": model_id,
#                 "sampling_params": params,
#                 "text": text,
#                 "web_sources": [],  # Initialize empty, will be filled by gemini
#                 "session_id": kwargs.get("session_id"),  # Add session_id
#                 "cached_web_sources": kwargs.get("cached_web_sources")  # Pass cached sources
#             }
#             total = ""
#             async for chunk in cls._gemini_api.inference(api_job_info):
#                 total += chunk
#                 yield chunk
            
#             # Lấy web_sources từ api_job_info sau khi inference
#             web_sources = api_job_info.get("web_sources", [])
#             await job_info["finish_call"](total, web_sources)
#         else:
#             total = ""
#             job_info_id = job_info["id"]
#             async for chunk in KaggleManager.inference(job_info["domain"], job_id):
#                 total += chunk
#                 yield chunk
            
#             # Get stored sources from KaggleManager
#             web_sources, rag_sources = KaggleManager.get_stored_sources(job_info_id)
#             # Combine web_sources and rag_sources into one list for compatibility
#             all_sources = web_sources + rag_sources
#             await job_info["finish_call"](total, all_sources)
#     @classmethod
#     async def pre_inference(cls, text: str, model_id: str, params: GenerationParams, session_id: str) -> ModelPreOutput | None:
#         job_id = generate_id()
#         server_kwargs: dict | None = None
#         if model_id.startswith("api:"):
#             # Get web search params and pre-compute sources for pre_output
#             k_pages = params.get("k_pages", 0)
#             domain_restrict = params.get("domain_restrict", False)
            
#             # Pre-compute web sources to include in response
#             web_sources = []
#             if k_pages > 0:
#                 try:
#                     gemini_temp = GeminiAPIModel()
#                     _, web_sources = gemini_temp.build_prompt_with_web_search(text, k_pages, domain_restrict)
#                 except Exception as e:
#                     web_sources = []
            
#             pre_output: ModelPreOutput = {
#                 "stream_id": job_id,
#                 "model_id": model_id,
#                 "user_summary": text,
#                 "user_intent": text,
#                 "user_keywords": [],
#                 "generation_params": params,
#                 "web_sources": web_sources,
#                 "rag_sources": [],
#                 "extra_data": {}
#             }
#             domain = ""
#             server_kwargs = {
#                 "model_id": GEMINI_MODEL,
#                 "text": text,
#                 "generation_params": params,
#                 "session_id": session_id,  # Add session_id
#                 #"cached_web_sources": web_sources  # Cache web sources to avoid duplicate search :)) Please NOOO
#             }
#         else:
#             # If we have a session_id, try to include past messages as history
#             # Note: session_id is alway not None. We create it before attempt to run model
#             history = None
#             if session_id:
#                 try:
#                     msgs = await get_history(session_id, loader=load_history_from_db)
#                     history = [
#                         {"role": ("assistant" if m.role == "bot" else "user"), "content": m.text}
#                         for m in msgs
#                     ]
#                 except Exception:
#                     history = None
                    
#             pack = await KaggleManager.pre_inference(job_id, text, model_id, params, history)
#             if pack != None:
#                 domain, pre_output = pack
#             else:
#                 return None
#         job_info: JobInfo = {
#             "domain": domain,
#             "id": job_id,
#             "server_kwargs": server_kwargs
#         }
#         cls._jobs[job_id] = job_info
#         return pre_output
#     @classmethod
#     async def get_models(cls) -> list[ModelInfo]:
#         result: list[ModelInfo] = [
#             {
#                 "name": "Gemini (Server)",
#                 "id": f"api:{GEMINI_MODEL}",
#                 "streaming": False,
#                 "source": "server"
#             }
#         ]
#         result.extend(await KaggleManager.get_models())
#         return result
#     @classmethod
#     async def store_chat(cls, user_id: str, session_id: str, user_text: str, user_timestamp: datetime, model_output: ModelOutput):
#         """Update chat on database"""
#         bot_timestamp = datetime.now(timezone.utc)
#         user_msg_id, bot_msg_id = await add_conversation(
#             user_id=user_id,
#             session_id=session_id,
#             user_text=user_text,
#             user_summary=model_output["user_summary"],
#             user_keywords=model_output["user_keywords"],
#             user_intent=model_output["user_intent"],
#             bot_text=model_output["text"],
#             bot_summary=model_output["bot_summary"],
#             bot_keywords=model_output["bot_keywords"],
#             answer_state=model_output["answer_state"],
#             model_id=model_output["model_id"],
#             web_sources=model_output["web_sources"],
#             rag_sources=model_output["rag_sources"],
#             params=model_output["generation_params"],
#             user_timestamp=user_timestamp,
#             bot_timestamp=bot_timestamp, # Does not prevent incorrect order
#             user_extra_data={},
#             bot_extra_data=model_output["extra_data"]
#         )