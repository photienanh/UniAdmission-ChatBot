import google.generativeai as genai
from google.generativeai.types import GenerationConfig
import os
from typing import AsyncGenerator, List, Tuple, Union, Optional

from .schema import APIJobInfo
from ..search.search_router import search
from config import GEMINI_SYSTEM_INSTRUCTION

class GeminiAPIModel:
    def __init__(self) -> None:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    
    def merge_context(self, question: str, web_sources: Optional[List[dict]]) -> str:
        """Ghép prompt từ câu hỏi + nguồn tham khảo"""
        if web_sources:
            context = ""
            for source in web_sources:
                context += f"{source['text']}\n\n" + 100 * "-" + "\n\n" if source['text'] != "Không thể trích xuất nội dung" else ""
            return f"Thông tin tham khảo:\n{context}\nCâu hỏi: {question}"
        return f"Câu hỏi: {question}"
    
    def build_prompt(self, question: str, k_pages: int, domain_restrict: bool = False) -> Tuple[str, List[dict]]:
        """Tạo prompt với web search context"""
        
        if k_pages > 0:
            # Thực hiện web search
            try:
                search_sources = search(question, k_pages, domain_restrict)
            except Exception as e:
                return question, []
            if domain_restrict:
                edu_sources = [s for s in search_sources if '.edu.vn' in s.get('url', '')]
                if edu_sources:
                    search_sources = edu_sources
            if search_sources is None:
                prompt = self.merge_context(question, [])
                return prompt, []
            
            prompt = self.merge_context(question, search_sources)
            return prompt, search_sources
        else:
            return self.merge_context(question, []), []
        
    async def inference(self, info: APIJobInfo) -> AsyncGenerator[str, None]:
        sampling_params = info["sampling_params"]
        config = GenerationConfig(
            temperature=sampling_params.get("temperature", 0.8),
            top_p=sampling_params.get("top_p", 0.9),
            max_output_tokens=sampling_params.get("max_tokens", 4096)
        )

        conversation_history = info.get("conversation", [])

        # Create model instance with system instruction (including web context)
        model = genai.GenerativeModel(info["model_id"], system_instruction=GEMINI_SYSTEM_INSTRUCTION)
        
        # Generate content với conversation history và streaming
        response = model.generate_content(
            contents=conversation_history,
            generation_config=config,
            stream=True
        )
        
        # Iterate through chunks synchronously trong async function
        response_received = False
        for chunk in response:
            try:
                # Check if chunk has parts and candidates
                if hasattr(chunk, 'candidates') and chunk.candidates:
                    candidate = chunk.candidates[0]
                    if hasattr(candidate, 'content') and candidate.content and candidate.content.parts:
                        # Try to get text from parts
                        text_content = ""
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text_content += part.text
                        
                        if text_content:
                            response_received = True
                            yield text_content
                        
                # Fallback to original method if above doesn't work
                elif hasattr(chunk, 'text'):
                    text = chunk.text
                    if text:
                        response_received = True
                        yield text
                        
            except ValueError as e:
                # Handle case where chunk.text is invalid (finish_reason != None)
                if "finish_reason" in str(e):
                    # This chunk finished without text, skip it
                    continue
                else:
                    # Re-raise other ValueError
                    raise e
            except Exception as e:
                # Handle other potential errors
                continue
        
        # If no response was received, yield empty string to prevent hanging
        if not response_received:
            yield ""