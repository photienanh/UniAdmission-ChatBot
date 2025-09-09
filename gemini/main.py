from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv("gemini.env")

from server import *
from typing import AsyncGenerator
from gemini_ import GeminiAPIModel
from vector_cache import vector_cache_manager, VECTOR_INDEX_PATH

GEMINI_MODEL = "gemini-2.5-flash"

gemini_model = GeminiAPIModel()
# Inference
REQUEST_STORAGE: dict[str, tuple[str, WorkerChatRequest, ModelPreOutput]] = {}
async def pre_inference_function(request: WorkerChatRequest) -> ModelPreOutput:
    print(f"[Gemini] Receive job: {request["text"]}")
    print(request["params"])
    params = request["params"]
    k_pages = params.get("k_pages", 0)
    domain_restrict = params.get("domain_restrict", False)
    text = request["text"]
    stream_id = request["stream_id"]
    
    prompt, web_sources = gemini_model.build_prompt_with_web_search(text, k_pages, domain_restrict)
    pre_output: ModelPreOutput = {
        "model_id": GEMINI_MODEL,
        "generation_params": params,
        "web_sources": web_sources,
        "rag_sources": [],
        "extra_data": {},
        "result_url": stream_id # Auto add domain and route when send back, just put stream id here
    }
    REQUEST_STORAGE[request["stream_id"]] = (prompt, request, pre_output)
    return pre_output

async def inference_function(stream_id: str) -> AsyncGenerator[str, None]:
    prompt, request, pre_output = REQUEST_STORAGE.pop(stream_id)
    generator = gemini_model.inference(request)
    total = ""
    try:
        async for chunk in generator:
            total += chunk
            yield chunk
    finally:
        # Store chat data when finish
        model_output: ModelOutput = {
            **pre_output,
            "text": total
        }
        data: WorkerStoreChatData = {
            "forward_kwargs": request["forward_kwargs"],
            "model_output": model_output
        }
        await app.state.store_chat(data)


# Server info
MODELS: list[ModelInfo] = [
    {
        "name": "Gemini server",
        "id": GEMINI_MODEL
    }
]
MODEL_STATUS = [ModelStatus(**model, active=True, scheduled=True, active_count=999, scheduled_count=999) for model in MODELS]
CLIENT_INFO: WorkerServerInfo = {
    "name": "Gemini test",
    "domain": "http://127.0.0.1:8002",
    "models": MODEL_STATUS
}
DOMAIN = "http://127.0.0.1:8000"
app = construct_app(
    server_domain=DOMAIN,
    info=CLIENT_INFO,
    pre_inference=pre_inference_function,
    inferece=inference_function,
    init_tasks=[
        vector_cache_manager.startup(
            index_path=VECTOR_INDEX_PATH,
            refresh_interval=900
        )
    ],
    shutdown_tasks=[
        vector_cache_manager.shutdown()
    ],
    is_local=True
)

# CORS policy
from fastapi.middleware.cors import CORSMiddleware
origins = [
    "http://127.0.0.1:8000"
]
ngrok_regex = r"https:\/\/.*\.ngrok-free\.app"
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=ngrok_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Run with python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8002)