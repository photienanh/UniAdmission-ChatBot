from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv("gemini.env")

from server import *
from typing import AsyncGenerator
from gemini import GeminiAPIModel

REQUEST_STORAGE: dict[str, tuple[str, WorkerChatRequest]] = {}
GEMINI_MODEL = "gemini-2.5-flash"

gemini_model = GeminiAPIModel()
async def pre_inference_function(request: WorkerChatRequest) -> ModelPreOutput:
    print(f"[Gemini] Receive job: {request["text"]}")
    params = request["params"]
    k_pages = params.get("k_pages", 0)
    domain_restrict = params.get("domain_restrict", False)
    text = request["text"]
    stream_id = request["stream_id"]
    
    prompt, web_sources = gemini_model.build_prompt_with_web_search(text, k_pages, domain_restrict)
    pre_output: ModelPreOutput = {
        "model_id": GEMINI_MODEL,
        "user_summary": text,
        "user_intent": text,
        "user_keywords": [],
        "generation_params": params,
        "web_sources": web_sources,
        "rag_sources": [],
        "extra_data": {},
        "result_url": f"http://127.0.0.1:8002/inference/{stream_id}"#f"http://13.215.102.203:8002/inference/{stream_id}"
    }
    print(request["params"])
    REQUEST_STORAGE[request["stream_id"]] = (prompt, request)
    return pre_output

async def inference_function(stream_id: str) -> AsyncGenerator[str, None]:
    prompt, request = REQUEST_STORAGE.pop(stream_id)
    generator = gemini_model.inference(request)
    return generator

MODELS: list[ModelInfo] = [
    {
        "name": "Gemini server",
        "id": GEMINI_MODEL,
        "streaming": True
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
    ],
    is_local=True
)
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