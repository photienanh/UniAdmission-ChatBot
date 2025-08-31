import google.generativeai as genai
from google.generativeai.types import GenerationConfig
import os
from typing import AsyncGenerator

# from history_cache import get_history, Msg
from web_search import get_source
from config import SYSTEM_INSTRUCTION
from server import WorkerChatRequest

class GeminiAPIModel:
    def __init__(self) -> None:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY")) #type:ignore
    
    def compose_prompt(self, question: str, web_sources: list[dict]) -> str:
        """Ghép prompt từ câu hỏi + nguồn tham khảo"""
        if web_sources:
            context = ""
            for source in web_sources:
                context += f"{source['text']}\n\n" + 100 * "-" + "\n\n"
            return f"Thông tin tham khảo:\n{context}\nCâu hỏi: {question}"
        return f"Câu hỏi: {question}"
    
    def build_prompt_with_web_search(self, question: str, k_pages: int, domain_restrict: bool = False):
        """Tạo prompt với web search context"""
        
        if k_pages > 0:
            # Thực hiện web search
            try:
                search_sources = get_source(question, k_pages, domain_restrict)
            except Exception as e:
                return question, []
            if domain_restrict:
                edu_sources = [s for s in search_sources if '.edu.vn' in s.get('url', '')] #type:ignore
                if edu_sources:
                    search_sources = edu_sources
            if search_sources is None:
                return question, []
                
            prompt = self.compose_prompt(question, search_sources)
            return prompt, search_sources
        else:
            return self.compose_prompt(question, []), []
        
    async def inference(self, info: WorkerChatRequest) -> AsyncGenerator[str, None]:
        params = info["params"]
        config = GenerationConfig(
            temperature=params.get("temperature", 0.8),
            top_p=params.get("top_p", 0.9),
            max_output_tokens=params.get("max_tokens", 4096)
        )
        
        # Lấy thông tin web search từ params
        k_pages = params.get("k_pages", 0)
        domain_restrict = params.get("domain_restrict", False)
        
        # Build conversation history: prefer explicit `history` in info, else load from session_id
        current_question = info["text"]
        if info.get("cached_web_sources") is not None:
            web_sources = info["cached_web_sources"] #type:ignore
        else:
            _, web_sources = self.build_prompt_with_web_search(current_question, k_pages, domain_restrict)
        conversation_history = []
        try:
            history = info["history"]
            for m in history:
                if m["role"] == "user":
                    conversation_history.append({"role": "user", "parts": [{"text": m["text"]}]})
                else:
                    conversation_history.append({"role": "model", "parts": [{"text": m["text"]}]})
        except Exception:
            pass

        user_message = self.compose_prompt(current_question, web_sources)
        conversation_history.append({"role": "user", "parts": [{"text": user_message}]})

        # Create model instance with system instruction (including web context)
        model = genai.GenerativeModel(info["model_id"], system_instruction=SYSTEM_INSTRUCTION) #type:ignore
        
        # Generate content với conversation history và streaming
        # response = model.generate_content(
        #     contents=conversation_history,
        #     generation_config=config,
        #     stream=True
        # ) # Call with stream still block thread
        response = await model.generate_content_async(
            contents=conversation_history,
            generation_config=config,
            stream=True
        )
        
        # Iterate through chunks synchronously trong async function
        response_received = False
        async for chunk in response:
            text = chunk.text
            if text != None:
                # print(text)
                response_received = True
                yield text
                
            # WHAT codes below do ?
            # try:
            #     # Check if chunk has parts and candidates
            #     if hasattr(chunk, 'candidates') and chunk.candidates:
            #         candidate = chunk.candidates[0]
            #         if hasattr(candidate, 'content') and candidate.content and candidate.content.parts:
            #             # Try to get text from parts
            #             text_content = ""
            #             for part in candidate.content.parts:
            #                 if hasattr(part, 'text') and part.text:
            #                     text_content += part.text
                        
            #             if text_content:
            #                 response_received = True
            #                 yield text_content
                        
            #     # Fallback to original method if above doesn't work
            #     elif hasattr(chunk, 'text'):
            #         text = chunk.text
            #         if text:
            #             response_received = True
            #             yield text
                        
            # except ValueError as e:
            #     # Handle case where chunk.text is invalid (finish_reason != None)
            #     if "finish_reason" in str(e):
            #         # This chunk finished without text, skip it
            #         continue
            #     else:
            #         # Re-raise other ValueError
            #         raise e
            # except Exception as e:
            #     # Handle other potential errors
            #     continue
        
        # If no response was received, yield empty string to prevent hanging
        if not response_received:
            yield ""