"""Custom QA class for handling inference and web search integration"""

from typing import AsyncGenerator
from vllm_worker.vllm_engine import VLLMEngine, VLLMJobInfo
from web_search import CmdLogger, WebSearchWrapper
from .schema import KaggleRequest, GenerationParams, ModelPreOutput, WebSource, RagSource
from .config import DOC_TEMPLATE, PROMPT_TEMPLATE, SEP, LORA_MAPPER

class CustomQA:
    """Main QA class that handles model inference and web search integration"""
    
    def __init__(self, set_active_callback) -> None:
        self.engine = VLLMEngine(set_active_callback)
        self.logger = CmdLogger("QA")
        self.web_search = WebSearchWrapper()
    
    async def start(self):
        """Initialize the QA system"""
        await self.web_search.start()
        print(f"[CustomQA] Initialized successfully")
    
    async def preload(self, model_id: str):
        """Preload model to avoid waiting time on first request"""
        self.logger.start()
        vllm_in: VLLMJobInfo = {
            "model_id": model_id,
            "message": "Hello",
            "sampling_params": {
                "n": 1,
                "max_tokens": 16
            },
            "lora_request": None,
            "history": []
        }
        print(f"[CustomQA] Preloading model: {model_id}")
        generator = await self.engine.process(vllm_in)
        async for _ in generator:
            pass
        print(f"[CustomQA] Model preloaded successfully: {model_id}")
        self.logger.end("Preload")
    
    async def inference(self, prompt: str, request: KaggleRequest) -> AsyncGenerator[str, None]:
        """Run model inference with the given prompt and request"""
        full_model_id = request["model_id"]
        # Only support local VLLM models now (no API models)
        if SEP in full_model_id:
            model_id, lora_int_id = full_model_id.split(SEP)
            lora = LORA_MAPPER[int(lora_int_id)]
        else:
            model_id = full_model_id
            lora = None
        
        history = request.get("history", [])
        info = {
            "message": prompt,
            "model_id": model_id,
            "sampling_params": request["params"],
            "lora_request": lora,
            "history": history
        }
        return await self.engine.process(info) #type:ignore
    
    async def pre_inference(
        self,
        model_id: str,
        user_question: str,
        stream_id: str,
        params: GenerationParams,
        vector_sources: list = None,
        web_search_keywords: list = None
    ) -> tuple[str, ModelPreOutput]:
        """Prepare inference by handling search and building context"""
        
        # Check vector sources từ app/ trước
        if vector_sources and len(vector_sources) > 0:
            # Đã có vector sources từ app
            web_sources = vector_sources
            rag_sources = []
            source_type = "vector_db_from_app"
            final_question = user_question
            
        else:
            # Không có vector sources từ app -> dùng web search
            k_pages = params.get("k_pages", 0)
            k_docs = params.get("k_docs", 0)
            
            if k_pages == 0 or k_docs == 0:
                web_sources = []
                rag_sources = []
                source_type = "disabled"
            else:
                # Sử dụng web_search_keywords nếu có, otherwise fallback to user_question
                if web_search_keywords:
                    # Update params để pass keywords xuống web search
                    params_with_keywords = params.copy()
                    params_with_keywords["web_search_keywords"] = web_search_keywords
                    web_sources, rag_sources = await self.web_search(user_question, user_question, params_with_keywords)
                else:
                    web_sources, rag_sources = await self.web_search(user_question, user_question, params)
                source_type = "web_search"
            
            final_question = user_question
        
        # Build context từ RAG sources (relevant chunks)  
        context_text = ""
        if len(rag_sources) > 0:
            for doc in rag_sources:
                content = DOC_TEMPLATE.format(
                    title=doc.get("title", ""),
                    url=doc.get("url", ""),
                    text=doc.get("text", "")
                )
                context_text += content
        else:
            for doc in web_sources:
                content = DOC_TEMPLATE.format(
                    title=doc.get("title", ""),
                    url=doc.get("url", ""),
                    text=doc.get("text", "")
                )
                context_text += content
        
        context_block = f"Thông tin tham khảo:\n{context_text}\n" if context_text else ""
        final_prompt = PROMPT_TEMPLATE.format(
            context_block=context_block,
            question=final_question,
        )
        
        self.logger.start()
        pre_output: ModelPreOutput = {
            "stream_id": stream_id,
            "model_id": model_id,
            "generation_params": params,
            "web_sources": web_sources,
            "rag_sources": rag_sources,
            "extra_data": {
                "source_type": source_type,
                "sources_count": len(web_sources)
            }
        }
        return final_prompt, pre_output
