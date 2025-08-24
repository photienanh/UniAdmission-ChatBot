from pyngrok import ngrok
from kaggle_secrets import UserSecretsClient
user_secrets = UserSecretsClient()
NGROK_KEY = user_secrets.get_secret("NGROK_KEY_2")

# Set ngrok authtoken
ngrok.set_auth_token(NGROK_KEY)

import os
# Only keep necessary environment variables for web search
os.environ["WEB_SEARCH_SSL"] = str(False)
os.environ["GOOGLE_SEARCH_API_KEY"] = "AIzaSyAtItbzZTJQijvT4A5ynzEWhY1YNXYWKNY"
os.environ["GOOGLE_SEARCH_CX"] = "9501a956284f141ab"
os.environ["BRAVE_SEARCH_API_KEY"] = "BSAbUIq8YC6VrPhwp688ST6Vtz7cyrH"
DOMAIN = "https://06240aaab2cd.ngrok-free.app"
NGROK_PORT = 8002

# Start ngrok tunnel using pyngrok
tunnel = ngrok.connect(NGROK_PORT, "http")
public_url = tunnel.public_url

print(f"Ngrok tunnel started!")
print(f"Public URL: {public_url}")

import requests
import io
import tarfile
import shutil
from typing import cast
def unpack(data: bytes, path: str):
    if os.path.exists(path): # Remove old code
        shutil.rmtree(path)
    with io.BytesIO(data) as tar_buffer:
        with tarfile.open(fileobj=tar_buffer, mode='r:gz') as tar:
            tar.extractall(path=path)
def unpack_p(name: str):
    unpack(requests.get(f"{DOMAIN}/script/{name}").content, name)
def unpack_pl(*names: str):
    for name in names:
        unpack_p(name)
unpack_pl(
    "vllm_worker", "web_search", "server"
)

from typing import Any
from web_search import CmdLogger, Websearch
from vllm_worker import prepare
from vllm_worker.vllm_engine import VLLMEngine, VLLMJobInfo
from server import *
from typing import AsyncGenerator
import uvicorn
import traceback
prepare()

EMBEDDING_NAME = "intfloat/multilingual-e5-small"

DOC_TEMPLATE = "[**{title}**]({url}):\n{text}\n"
PROMPT_TEMPLATE = """
Bạn là một AI tư vấn tuyển sinh đại học chuyên nghiệp. Hãy trả lời các câu hỏi một cách chính xác, hữu ích và thân thiện. Có thể sử dụng những thông tin được cung cấp để đưa ra câu trả lời hoặc lời khuyên tốt nhất. Nếu được cung cấp link nguồn thì thêm vào phần cuối câu trả lời, nếu không được cung cấp thì không thêm.
Thông tin tham khảo:\n{context}\n
Câu hỏi:\n{question}\n
Câu trả lời:
"""
HYDE_TEMPLATE = """
Hãy trả lời câu hỏi sau ngắn gọn trong 100 từ, khi không có thông tin, đưa ra ví dụ.\n
Câu hỏi:\n{question}\n
Câu trả lời:
"""
SEARCH_TEMPLATE = """Bạn là chuyên gia tạo từ khóa tìm kiếm thông minh. Nhiệm vụ: phân tích câu hỏi và tạo từ khóa giúp tìm được thông tin CĂN BẢN để LLM có thể suy luận ra câu trả lời.
CHIẾN LƯỢC TÌM KIẾM:

1. **Phân tích ý định câu hỏi**: Xác định thông tin gì cần thiết để trả lời
2. **Tìm nguồn thông tin gốc**: Thay vì tìm trực tiếp câu trả lời, tìm dữ liệu để suy luận
3. **Tối ưu từ khóa**: Dùng thuật ngữ chính thức, tên đầy đủ

VÍ DỤ THÔNG MINH:

Câu hỏi: Số tiến sĩ trong viện trí tuệ nhân tạo UET là bao nhiêu?
→ Cần: Danh sách giảng viên để đếm tiến sĩ
→ Từ khóa: danh sách giảng viên viện trí tuệ nhân tạo UET

Câu hỏi: Điểm chuẩn ngành CNTT Bách Khoa 2024?  
→ Cần: Bảng điểm chuẩn chính thức
→ Từ khóa: điểm chuẩn đại học Bách Khoa Hà Nội 2024

Câu hỏi: Học phí ngành AI VNU-UET như thế nào?
→ Cần: Bảng học phí chính thức  
→ Từ khóa: học phí đại học công nghệ VNU-UET 2024

Câu hỏi: Chương trình đào tạo ngành CNTT có môn gì?
→ Cần: Khung chương trình chi tiết
→ Từ khóa: chương trình đào tạo ngành công nghệ thông tin UET

Câu hỏi: Đại học Bách khoa
→ Cần: Thông tin Đại học Bách khoa
→ Từ khóa: đại học Bách khoa

Câu hỏi: Tuyển sinh Đại học Bách khoa
→ Cần: Thông tin tuyển sinh Đại học Bách khoa
→ Từ khóa: tuyển sinh đại học bách khoa

NGUYÊN TẮC:
- Thêm năm học nếu cần thông tin mới nhất
- Tìm danh sách, bảng, chương trình thay vì câu hỏi trực tiếp
- Ưu tiên trang web chính thức (.edu.vn)

Chỉ trả về từ khóa, không giải thích.\n
Câu hỏi: {question}
→ Từ khóa: """
SEP = "$$$"
SOURCE = "kaggle"
MODELS: list[ModelInfo] = [
    {
        "name": "Qwen 3 4B",
        "id": "Qwen/Qwen3-4B",
        "source": SOURCE,
        "streaming": True
    },
    {
        "name": "Qwen 3 4B LoRA Finetuned",
        "id": f"Qwen/Qwen3-4B{SEP}1",
        "source": SOURCE,
        "streaming": True
    }
]
MODEL_STATUS = [ModelStatus(**model, active=False, scheduled=False, active_count=0, scheduled_count=0) for model in MODELS]
CLIENT_INFO: KaggleServerInfo = {
    "name": "Testv1",
    "domain": "http://127.0.0.1:8002", # Auto change when run with ngrok
    "models": MODEL_STATUS
}
LORA_MAPPER = {
    1: {
        "lora_int_id": 1, # Same as key
        "lora_name": "Qwen Adapter v1",
        "lora_path": "/kaggle/input/qwen-lora-adapter/qwen_lora_adapter"
    }
}
PRELOAD_MODEL = "Qwen/Qwen3-4B"

def set_active(model_id: str):
    print(f"[Global] Switched to model {model_id}")
    if SEP in model_id:
        model_id = model_id.split(SEP)[0]
    for model in CLIENT_INFO["models"]:
        if model["id"].startswith(model_id):
            model["active"] = True
            model["scheduled"] = False
        else:
            model["active"] = False
            model["scheduled"] = False

class QueryRewrite:
    async def __call__(
        self, 
        text: str,
        params: GenerationParams
    ) -> tuple[str, str, str]:
        return text, text, text
    
class WebSearchWrapper:
    def __init__(self) -> None:
        self.web_search = Websearch(
            embedding_name=EMBEDDING_NAME, 
            device="cpu",
            chunk_size=1024, 
            chunk_overlap=128)
    async def start(self):
        await self.web_search.start()
    async def __call__(self, web_query: str, rag_query: str, params: GenerationParams) -> tuple[list[WebSource], list[RagSource]]:
        k_pages = params.get("k_pages", 0)
        k_docs = params.get("k_docs", 0)
        domain_restrict = params.get("domain_restrict", False)
        print(f"[WS] k_pages: {k_pages} | k_docs {k_docs} | domain_restrict: {domain_restrict}")
        if k_pages == 0 or k_docs == 0:
            return [], []
        else:
            web_sources, rag_sources = await self.web_search(
                web_query=web_query, rag_query=rag_query,
                k_pages=k_pages, k_docs=k_docs,
                domain_restrict=domain_restrict, engine="brave",
                include_pdf=False, include_image=False
            )
            return web_sources, rag_sources
        
class CustomQA:
    def __init__(self) -> None:
        self.engine = VLLMEngine(set_active)
        self.logger = CmdLogger("QA")
        self.query_rewriter = QueryRewrite()
        self.web_search = WebSearchWrapper()
    async def start(self):
        await self.web_search.start()
    async def delete(self):
        self.logger.start()
        del self.web_search
        self.logger.end("Unload")
    async def preload(self, model_id: str):
        vllm_in: VLLMJobInfo = {
            "model_id": model_id,
            "message": "Hello",
            "sampling_params": {
                "n": 1,
                "max_tokens": 16
            },
            "lora_request": None
        }
        generator = await self.engine.process(vllm_in)
        async for _ in generator:
            pass
    async def inference(self, prompt: str, request: KaggleRequest) -> AsyncGenerator[str, None]:
        full_model_id = request["model_id"]
        # Only support local VLLM models now (no API models)
        if SEP in full_model_id:
            parts = full_model_id.split(SEP)
            model_id = parts[0]
            lora = LORA_MAPPER[int(parts[1])]
        else:
            model_id = full_model_id
            lora = None
        info = {
            "message": prompt,
            "model_id": model_id,
            "sampling_params": request["params"],
            "lora_request": lora
        }
        return await self.engine.process(info) #type:ignore
    async def pre_inference(
        self,
        model_id: str,
        text: str,
        stream_id: str,
        params: GenerationParams
    ) -> tuple[str, ModelPreOutput]:
        question, web_query, rag_query = await self.query_rewriter(text, params)
        web_sources, rag_sources = await self.web_search(web_query, rag_query, params)
        
        context = ""
        for doc in rag_sources:
            content = DOC_TEMPLATE.format(
                title=doc["title"],
                url=doc["url"],
                text=doc["text"]
            )
            context += content
        prompt = PROMPT_TEMPLATE.format(context=context, question=question)
        self.logger.start()
        pre_output: ModelPreOutput = {
            "stream_id": stream_id,
            "model_id": model_id,
            "generation_params": params,
            "web_sources": web_sources,
            "rag_sources": rag_sources,
            "extra_data": {}
        }
        return prompt, pre_output
    
import threading
def thread_task():
    ws_pipeline = CustomQA()
    REQUEST_STORAGE: dict[str, tuple[str, KaggleRequest]] = {}
    async def pre_inference_function(request: KaggleRequest) -> ModelPreOutput:

        prompt, pre_output = await ws_pipeline.pre_inference(
            request["model_id"],
            request["text"],
            request["stream_id"],
            request["params"]
        )
        print(request["params"])
        REQUEST_STORAGE[request["stream_id"]] = (prompt, request)
        return pre_output
    
    async def inference_function(stream_id: str) -> AsyncGenerator[str, None]:
        prompt, request = REQUEST_STORAGE.pop(stream_id)
        generator = await ws_pipeline.inference(prompt, request)
        return generator
    
    app = construct_app(
        server_domain=DOMAIN,
        info=CLIENT_INFO,
        pre_inference=pre_inference_function,
        inferece=inference_function,
        init_tasks=[
            ws_pipeline.start(), 
            ws_pipeline.preload(PRELOAD_MODEL)
        ]
    )
    
    uvicorn.run(app, port=NGROK_PORT)
thread = threading.Thread(target=thread_task, daemon=True)
thread.start()