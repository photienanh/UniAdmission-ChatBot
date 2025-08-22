import google.generativeai as genai
from google.generativeai.types import GenerationConfig
import os
from typing import AsyncGenerator
from datetime import datetime, timezone

from .schema import APIJobInfo
from .web_search import get_source
from config import SYSTEM_INSTRUCTION

class GeminiAPIModel:
    def __init__(self) -> None:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
    def build_prompt_with_web_search(self, question: str, k_pages: int, domain_restrict: bool = False):
        """Tạo prompt với web search context"""
        
        if k_pages > 0:
            # Thực hiện web search
            try:
                search_sources = get_source(question, k_pages)
            except Exception as e:
                return question, []
                
            if search_sources is None:
                return question, []
                
            # Thêm timestamp cho sources
            for source in search_sources:
                source["timestamp"] = datetime.now(timezone.utc).isoformat()
                
            # Lọc theo domain nếu cần
            if domain_restrict:
                edu_sources = [s for s in search_sources if '.edu.vn' in s.get('url', '')]
                if edu_sources:
                    search_sources = edu_sources
                    
            # Tạo context từ search results
            context = ""
            for source in search_sources:
                context += f"{source['text']}\n\n" + 100 * '-' + "\n\n"
                
            prompt = f"""
Thông tin tham khảo:
{context}

Câu hỏi: {question}
"""
            return prompt, search_sources
        else:
            return question, []
        
    async def inference(self, info: APIJobInfo) -> AsyncGenerator[str, None]:
        params = info["sampling_params"]
        config = GenerationConfig(
            temperature=params.get("temperature", 0.8),
            top_p=params.get("top_p", 0.9),
            top_k=params.get("top_k", 16),
            max_output_tokens=params.get("max_tokens", 4096)
        )
        
        # Lấy thông tin web search từ params
        k_pages = params.get("k_pages", 0)
        domain_restrict = params.get("domain_restrict", False)
        
        # Tạo prompt với web search nếu cần
        prompt, web_sources = self.build_prompt_with_web_search(info["text"], k_pages, domain_restrict)
        
        # Lưu web_sources vào info để sử dụng sau này
        info["web_sources"] = web_sources
        
        # Tạo model instance với system instruction
        model = genai.GenerativeModel(
            info["model_id"],
            system_instruction=SYSTEM_INSTRUCTION
        )
        
        # Generate content với streaming (sync)
        response = model.generate_content(
            contents=prompt,
            generation_config=config,
            stream=True
        )
        
        # Iterate through chunks synchronously trong async function
        for chunk in response:
            if hasattr(chunk, 'text') and chunk.text:
                yield chunk.text