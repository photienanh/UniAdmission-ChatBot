DOMAIN = "http://127.0.0.1:8000"
DEPLOY_URL = None#"https://uniadmission.me"


IS_LOCAL = DOMAIN == "http://127.0.0.1:8000"
BASE_PATH = "" if IS_LOCAL else "/kaggle/working"

ws_pipeline = None

import os
import requests
import io
import tarfile
import shutil
def unpack_folder(data: bytes, path: str):
    if os.path.exists(path): # Remove old code
        shutil.rmtree(path)
    with io.BytesIO(data) as tar_buffer:
        with tarfile.open(fileobj=tar_buffer, mode='r:gz') as tar:
            tar.extractall(path=path)
def unpack_file(data: bytes, path: str):
    os.makedirs(f"{BASE_PATH}files", exist_ok=True)
    if os.path.exists(path):
        os.remove(path)
    with open(path, 'wb') as file:
        file.write(data)
def unpack_list(*names: str):
    # if DOMAIN == "http://127.0.0.1:8000": return
    for name in names:
        if "." in name:
            url = f"{DOMAIN}/package/{name}"
        else:
            url = f"{DOMAIN}/package/{name}"
        data = requests.get(url).content
        if "." in name:
            unpack_file(data, f"files/{name}")
        else:
            unpack_folder(data, name)
unpack_list(
    "worker.env", "school_name.json", "school_alias.json","local.pkl"
)

from dotenv import load_dotenv
load_dotenv(f"{BASE_PATH}files/worker.env")

NGROK_PORT = 8002
if DOMAIN != "http://127.0.0.1:8000":
    import subprocess
    subprocess.run(["ngrok", "config", "add-authtoken", os.getenv("NGROK_TOKEN_1", "")])
    subprocess.Popen(["ngrok", "http", str(NGROK_PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

# Replacement for cmd
    
from huggingface_hub import login
login(token=os.getenv("HUGGING_FACE_TOKEN"))

# cmd = [
#     "hf", "auth", "login",
#     "--token", os.getenv("HUGGING_FACE_TOKEN")
# ]
# import subprocess
# subprocess.run(cmd)
# print("")

from data_retriever import *
from server import *
from school_mapper import SchoolMapper
from typing import AsyncGenerator, NotRequired, Protocol
from typing import Callable, AsyncGenerator
from openai import AsyncOpenAI, OpenAI
from google import genai
from google.genai import types
import os
import pickle
import json
import asyncio
import enum
import traceback
import copy

from typing import Protocol, AsyncGenerator, TypedDict
class KeywordInfo(TypedDict):
    query: str
    priority: float
    info: str
    school: str
class KeywordModelProtocol(Protocol):
    async def keywords(self, question: str, params: GenerationParams, threshold: float = 0.5) -> list[KeywordInfo]: ...
class RouterModelProtocol(Protocol):
    async def route(self, question: str, params: GenerationParams) -> list[dict]: ...
    
MODEL_ID = "Qwen/Qwen3-4B"
# Retriever config
search_config = WebsearchConfig(
    page_timeout=15,
    file_timeout=15,
)
rag_config = RagConfig(
    embedding_name="intfloat/multilingual-e5-small",
    device="cpu"
)
splitter_config = SplitterConfig(
    tokenizer_name=MODEL_ID,
    chunk_size=512,
    chunk_overlap=0,
    device="cpu"
)
table_merge_config = MergeTableConfig(
    k_max_previous=5,
    k_max_next=5
)
neighbor_config = MergeNeighborConfig(
    k_previous_chunks=1,
    k_next_chunks=1
)
# Sampling Params
PAGE_RERANKER_PARAMS = {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 4096
}
KEYWORDS_PARAMS = {
    "temperature": 0.5,
    "top_p": 0.9,
    "max_tokens": 4096
}
ROUTER_PARAMS = {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 1024
}
MODELS: list[ModelInfo] = [
    {
        "name": "GPT 4o mini",
        "id": "gpt-4o-mini"
    },
    {
        "name": "Gemini 2.5 flash",
        "id": "gemini-2.5-flash"
    }
]
CLIENT_INFO: WorkerServerInfo = {
    "name": "Test API",
    "domain": "http://127.0.0.1:8002", # Auto change when run with ngrok
    "models": MODELS
}

from instruction import *

class LocalRetriever:
    """Search in static db"""
    def __init__(self) -> None:
        with open(f"{BASE_PATH}files/local.pkl", 'rb') as file:
            self.all_docs = pickle.load(file)
    def _filter_docs(self, school_id: str, section: str) -> list:
        school_docs = [doc for doc in self.all_docs if doc.metadata.get("school_id") == school_id]
        if school_docs:
            filtered_docs = [doc for doc in school_docs if doc.metadata.get("section") == section]
        else:
            filtered_docs = []
        return filtered_docs
    def retrieve(self, keywords: list[dict]) -> tuple[list[WebSource], list[RagSource]]:
        web_sources: list[WebSource] = []
        rag_sources: list[RagSource] = []
        try:
            for kw in keywords:
                school_id = kw.get("school_id")
                section = kw.get("section")
                if school_id and section:
                    docs = self._filter_docs(school_id, section)
                    title = f"Tìm trường ĐH-CĐ - Cốc Cốc ({school_id})"
                    combined_content = "\n\n".join([doc.page_content for doc in docs])
                    description = combined_content[:100] + "..." if len(combined_content) > 100 else combined_content
                    web_source: WebSource = {
                        "query": f"{school_id}:{section}",
                        "title": title,
                        "description": description,
                        "url": "https://hoctap.coccoc.com/tim-truong-dh-cd",
                        "text": combined_content,
                        "files": [],
                        "score": 1
                    }
                    rag_source: RagSource = {
                        "chunk_index": 0,
                        "query": f"{school_id}:{section}",
                        "title": title,
                        "url": "https://hoctap.coccoc.com/tim-truong-dh-cd",
                        "text": combined_content,
                    }
                    web_sources.append(web_source)
                    rag_sources.append(rag_source)
        except:
            traceback.print_exc()
        finally:            
            return web_sources, rag_sources
        
class WebRetriever:
    """Search in web"""
    def __init__(self, llm_ranker: PageRerankModelProtocol, llm_keywords: KeywordModelProtocol) -> None:
        self.pipeline = DataRetrieverPipeline(
            llm_ranker,
            websearch_config=search_config,
            rag_config=rag_config,
            splitter_config=splitter_config,
            neighbor_merge_config=neighbor_config,
            table_merge_config=table_merge_config
        )
        self.llm_keywords = llm_keywords
        self.school_mapper = SchoolMapper(f"{BASE_PATH}files/school_name.json")
    async def start(self):
        """Initialize websearch"""
        await self.pipeline.start()
    async def retrive(self, question: str, params: GenerationParams) -> tuple[list[WebSource], list[RagSource]]:
        data = await self.llm_keywords.keywords(question, params)
        max_query = params.get("max_query", 1)
        queries = []
        school_restrict = params.get("school_domain", False)
        for item in data:
            if not school_restrict:
                queries.append(item["query"])
            else:
                school = item["school"]
                if school.strip() != "":
                    school_domains = self.school_mapper.domains_from_auto(school, 5)[:10]
                    print(f"[DOMAINS]", school_domains)
                    if len(school_domains) > 0:
                        queries.append([item["query"], school_domains])
        return await self.pipeline.retrieve(params, queries[:max_query])
    
class RouterRetriever:
    def __init__(self, llm_router: RouterModelProtocol, web_retriever: WebRetriever, local_retriever: LocalRetriever) -> None:
        self.web_retriever = web_retriever
        self.local_retriever = local_retriever
        self.router = llm_router
    async def retrieve(self, question: str, params: GenerationParams) -> tuple[list[WebSource], list[RagSource]]:
        use_websearch = params.get("use_websearch", False) and params.get("max_query", 0) > 0 and params.get("k_docs", 0) > 0 and params.get("k_pages", 0) > 0
        use_localdb = params.get("use_localdb", False)
        if use_websearch and use_localdb:
            local_queries = await self.router.route(question, params)
            if len(local_queries) > 0:
                return self.local_retriever.retrieve(local_queries)
            else:
                return await self.web_retriever.retrive(question, params)
        elif use_localdb:
            local_queries = await self.router.route(question, params)
            if len(local_queries) > 0:
                return self.local_retriever.retrieve(local_queries)
            else:
                return [], []
        elif use_websearch:
            return await self.web_retriever.retrive(question, params)
        else:
            return [], []
        
import openai
class APIModelCore:
    def __init__(self) -> None:
        self.gpt_client = AsyncOpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.logger = CmdLogger("Model")
    async def call(self, call_type: CallType, instruction: str, prompt: str, params: GenerationParams) -> AsyncGenerator[str, None]:
        print(f"[API] {call_type} | Instruction length: {len(instruction)} | Prompt length: {len(prompt)} | kwargs: {params.get('kwargs')}")
        model_id = params["model_id"]
        if "gpt" in model_id:
            while True:
                try:
                    stream = await self.gpt_client.chat.completions.create(
                        model=model_id, 
                        messages=[
                            {"role": "system", "content": instruction},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=params.get("max_tokens", 4096),
                        temperature=params.get("temperature", 0.7),
                        top_p=params.get("top_p", 0.9),
                        presence_penalty=params.get("presence_penalty", 0.1),
                        frequency_penalty=params.get("frequency_penalty", 0.0),
                        stream=True
                    )
                    total_text = ""
                    async for event in stream:
                        chunk = event.choices[0].delta.content
                        if chunk is not None:
                            total_text += chunk
                            yield chunk
                    return
                except openai.APIError as e:
                    print(e)
        else:
            gemini_config = types.GenerateContentConfig(
                temperature=params.get("temperature", 0.8),
                top_p=params.get("top_p", 0.9),
                top_k=params.get("top_k", 16),
                max_output_tokens=params.get("max_tokens", 4048)
            )
            stream = await self.gemini_client.aio.models.generate_content_stream(
                model=model_id,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=instruction)]
                    ),
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=prompt)]
                    )
                ],
                config=gemini_config
            )
            async for chunk in stream:
                if chunk.candidates:
                    if chunk.candidates[0].content:
                        if chunk.candidates[0].content.parts:
                            for part in chunk.candidates[0].content.parts:
                                if part.text:
                                    yield part.text
    async def __call__(self, call_type: CallType, instruction: str, prompt: str, params: GenerationParams) -> AsyncGenerator[str, None]:
        return self.call(call_type, instruction, prompt, params)
    
class APIModel(APIModelCore):
    async def route(self, question: str, params: GenerationParams) -> list[dict]:
        text = ""
        prompt = ROUTER_TEMPLATE.format(question=question)
        copy_params = copy.deepcopy(params)
        copy_params.update(ROUTER_PARAMS) #type:ignore 
        async for chunk in await self(
            call_type=CallType.ROUTER, 
            instruction=ROUTER_INSTRUCTION+ROUTER_PREFIX, 
            prompt=prompt, 
            params=copy_params
        ):
            text += chunk
        try:
            self.logger.log(text)
            result = json.loads(extract_json(text))
            return result
        except:
            traceback.print_exc()
            return []
    async def _llm_rerank_page(self, pages: list[SearchResult], query: str, relative_threshold: float, params: GenerationParams) -> list[SearchResult]:
        if len(pages) == 0: return []
        text = ""    
        scores = [0.0 for _ in pages]
        prompt = self._construct_reranker_prompt(query, pages)
        copy_params = copy.deepcopy(params)
        copy_params.update(PAGE_RERANKER_PARAMS) #type:ignore
        async for chunk in await self(
            call_type=CallType.RANKER, 
            instruction=PAGE_RERANKER_INSTRUCTION+PAGE_RERANKER_PREFIX, 
            prompt=prompt, 
            params=copy_params
        ):
            text += chunk
        try:
            self.logger.log(text)
            result = json.loads(extract_json(text))
            if "output" in result:
                for item in result["output"]:
                    index = int(item["index"]) - 1
                    scores[index] = float(item["score"])
            else:
                # Fallback if model not provide intermediate step
                for item in result:
                    index = int(item["index"]) - 1
                    scores[index] = float(item["score"])
        except:
            traceback.print_exc()
        self.logger.log("-----Original-----")
        if self.logger._enable:
            for page in pages:
                self.logger.log(f'{page["score"]:.3f} + {page["title"]}')
        max_score = 0
        for score, search_result in zip(scores, pages):
            max_score = max(max_score, score)
            search_result["score"] = score
        if max_score == 0: return []
        
        results: list[SearchResult] = []
        for search_result in pages:
            if search_result["score"] >= max_score * relative_threshold:
                results.append(search_result)
        results = sorted(results, key=lambda r:r["score"], reverse=True)
        self.logger.log("-----Reorder-----")
        if self.logger._enable:
            for page in results:
                self.logger.log(f'{page["score"]:.3f} + {page["title"]}')
        return results
    def _construct_reranker_prompt(self, query: str, data: list[SearchResult]) -> str:
        candidates = [{
            "index": index+1, 
            "title": item["title"],
            "description": item["description"],
        } for index, item in enumerate(data)]
        candidates = "[" + ",\n".join([json.dumps(item, ensure_ascii=False) for item in candidates]) + "]"
        return PAGE_RERANKER_TEMPLATE.format(query=query, pages=candidates)
    async def keywords(self, question: str, params: GenerationParams, threshold: float = 0.5) -> list[KeywordInfo]:
        num_queries = params.get("max_query", 1)
        copy_params = copy.deepcopy(params)
        copy_params.update(KEYWORDS_PARAMS) #type:ignore
        prompt = KEYWORD_TEMPLATE.format(question=question)
        text = ""
        async for chunk in await self(
            call_type=CallType.KEYWORDS, 
            instruction=KEYWORDS_INTRUCTION, 
            prompt=KEYWORDS_PREFIX.replace("{num}", str(num_queries))+prompt, 
            params=copy_params
        ):
            text += chunk
        try:
            self.logger.log(text)
            result: list[KeywordInfo] = json.loads(extract_json(text))
            for item in result:
                self.logger.log(item)
            return result
        except:
            print(text)
            traceback.print_exc()
            return []
    async def _heristic_rerank_page(self, pages: list[SearchResult], query: str, relative_threshold: float, params: GenerationParams) -> list[SearchResult]:
        """Rerank search results using embedding similarity"""
        self.logger.log("-----Original-----")
        if self.logger._enable:
            for page in pages:
                self.logger.log(f'{page["score"]:.3f} + {page["title"]}')
        import numpy as np
        def normalize_text(text: str) -> str:
            text = text.lower().strip()
            text = re.sub(r"[^a-zA-Z0-9\u00C0-\u1EF9\s\.,;]", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return text
        def detect_school(query: str, schools: dict) -> str | None:
            """Detect school from query using predefined keywords"""
            for school, aliases in schools.items():
                if any(alias in query for alias in aliases):
                    return school
            return None
        schools = {
            school: [normalize_text(alias) for alias in aliases]
            for school, aliases in json.load(open(f"{BASE_PATH}files/school_alias.json", "r", encoding="utf-8")).items()
        }
        embedding = ws_pipeline.retriever.web_retriever.pipeline._rag.embedding
        
        # If no embedding model available, return original results
        if not embedding:
            return pages
        
        query_norm = normalize_text(query)
        detected_school = detect_school(query_norm, schools)
        
        try:
            query_emb = embedding.embed_query(query_norm)
            max_score = 0
            for page in pages:
                title = page.get("title", "") or ""
                desc = page.get("description", "") or ""
                url = page.get("url", "") or ""

                # Chuẩn hóa
                title_norm = normalize_text(title)
                desc_norm = normalize_text(desc)
                url_norm = normalize_text(url)

                # Semantic embedding
                title_emb = embedding.embed_query(title_norm) if title_norm else None
                desc_emb = embedding.embed_query(desc_norm) if desc_norm else None
                url_emb = embedding.embed_query(url_norm) if url_norm else None

                # Cosine similarity
                def cos_sim(a, b):
                    norm_a = np.linalg.norm(a)
                    norm_b = np.linalg.norm(b)
                    if norm_a == 0 or norm_b == 0:
                        return 0.0
                    return float(np.dot(a, b) / (norm_a * norm_b))

                score = 0.0
                weights = {"title": 0.5, "desc": 0.3, "url": 0.2}
                if title_emb is not None:
                    score += cos_sim(query_emb, title_emb) * weights["title"]
                if desc_emb is not None:
                    score += cos_sim(query_emb, desc_emb) * weights["desc"]
                if url_emb is not None:
                    score += cos_sim(query_emb, url_emb) * weights["url"]

                # Heuristic ưu tiên trường trong query
                if detected_school:
                    aliases = [normalize_text(a) for a in schools.get(detected_school, [])]
                    if any(a in text for a in aliases for text in [url_norm, title_norm, desc_norm]):
                        score += 0.5
                    else:
                        for school, other_aliases in schools.items():
                            if school != detected_school:
                                other_aliases_norm = [normalize_text(a) for a in other_aliases]
                                if any(a in text for a in other_aliases_norm for text in [url_norm, title_norm, desc_norm]):
                                    score -= 0.5

                # Heuristic boost
                if any(kw in query_norm for kw in ["tuyển sinh", "ngành đào tạo"]):
                    if "tuyensinh247" in url_norm:
                        score += 0.1
                    if url_norm.endswith(".edu") or ".edu.vn" in url_norm:
                        score += 0.2
                page["score"] = score
                max_score = max(score, max_score)
            threshold_score = max_score * relative_threshold
            # Sort theo score giảm dần
            results = []
            for page in pages:
                if page["score"] >= threshold_score:
                    results.append(page)
            results = sorted(results, key=lambda x: x["score"], reverse=True)
            self.logger.log("-----Reorder-----")
            if self.logger._enable:
                for page in results:
                    self.logger.log(f'{page["score"]:.3f} + {page["title"]}')
            return results
            
        except Exception:
            # If any error occurs, return original results
            return pages
    async def rerank_page(self, pages: list[SearchResult], query: str, relative_threshold: float, params: GenerationParams) -> list[SearchResult]:
        use_llm_rerank = params.get("llm_rerank", False)
        if use_llm_rerank:
            return await self._llm_rerank_page(pages, query, relative_threshold, params)
        else:
            return await self._heristic_rerank_page(pages, query, relative_threshold, params)
        
class CombinedProtocol(ModelProtocol, KeywordModelProtocol, PageRerankModelProtocol, RouterModelProtocol):
    pass
class CustomQA:
    def __init__(self, model_protocol: CombinedProtocol) -> None:
        self.logger = CmdLogger("QA")
        web_retriever = WebRetriever(model_protocol, model_protocol)
        local_retriever = LocalRetriever()
        self.retriever = RouterRetriever(
            model_protocol,
            web_retriever,
            local_retriever
        )
        self.llm_call = model_protocol
    async def start(self):
        await self.retriever.web_retriever.start()
    async def inference(self, prompt: str, request: WorkerChatRequest) -> AsyncGenerator[str, None]:
        text = ""
        async for chunk in await self.llm_call(
            call_type=CallType.READER, 
            instruction=READER_UNTRAINED_INSTRUCTION+READER_UNTRAINED_PREFIX, 
            prompt=prompt, 
            params=request["params"]
        ):
            text += chunk
            yield chunk
    async def pre_inference(
        self,
        question: str,
        stream_id: str,
        params: GenerationParams
    ) -> tuple[str, ModelPreOutput]:
        web_sources, rag_sources = await self.retriever.retrieve(
            question, 
            params
        )
        context = SourceFormat()(rag_sources)
        prompt = READER_TEMPLATE.format(context=context, question=question)
        self.logger.start()
        pre_output: ModelPreOutput = {
            "generation_params": params,
            "web_sources": web_sources,
            "rag_sources": rag_sources,
            "extra_data": {
            },
            "result_url": stream_id,
        }
        return prompt, pre_output
    
async def main():
    global ws_pipeline
    api_model = APIModel()

    ws_pipeline = CustomQA(api_model)
    await ws_pipeline.start()
    import uuid
    class ServerModelImplement(ServerModel):  
        def __init__(self) -> None:
            self.request_storage: dict[str, tuple[str, WorkerChatRequest, ModelPreOutput]] = {}
        async def pre_inference(self, request: WorkerChatRequest) -> ModelPreOutput:
            stream_id = str(uuid.uuid4())
            params = request["params"]
            print(params)
            prompt, pre_output = await ws_pipeline.pre_inference(
                request["text"],
                stream_id,
                request["params"]
            ) 
            self.request_storage[stream_id] = (prompt, request, pre_output)
            return pre_output
        async def inference(self, stream_id: str) -> AsyncGenerator[str, None]:
            prompt, request, pre_output = self.request_storage.pop(stream_id)
            generator = ws_pipeline.inference(prompt, request)
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
                await self.store(data)
                
    server_model = ServerModelImplement()
    app = construct_app(
        server_domain=DOMAIN,
        info=CLIENT_INFO,
        server_model=server_model,
        init_tasks=[],
        shutdown_tasks=[],
        is_local=IS_LOCAL,
        deploy_url=DEPLOY_URL
    )
    # CORS policy
    from fastapi.middleware.cors import CORSMiddleware
    origins = [
        "http://127.0.0.1:8000",
        "https://uniadmission.me",
        DOMAIN
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    import uvicorn

    uvicorn_config = uvicorn.Config(app, port=NGROK_PORT)
    uvicorn_server = uvicorn.Server(uvicorn_config)
    await uvicorn_server.serve()
    
asyncio.run(main())