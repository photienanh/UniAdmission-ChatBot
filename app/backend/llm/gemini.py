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
                search_sources = get_source(question, k_pages, domain_restrict)
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
        
        # Check if web sources are already cached from pre-inference
        cached_web_sources = info.get("cached_web_sources")
        if cached_web_sources is not None:
            # Use cached web sources to avoid duplicate search
            web_sources = cached_web_sources
            current_question = info["text"]  # Use original question
        else:
            # Perform fresh web search if no cached sources
            current_question = info["text"]
            prompt, web_sources = self.build_prompt_with_web_search(current_question, k_pages, domain_restrict)
        
        # Lưu web_sources vào info để sử dụng sau này
        info["web_sources"] = web_sources
        
        # Build conversation history if session_id exists
        conversation_history = []
        session_id = info.get("session_id")
        if session_id:
            try:
                from database.crud.chat import get_session_with_messages
                chat_session = await get_session_with_messages(session_id)
                if chat_session and chat_session.messages:
                    # Convert messages to Gemini format (exclude current message)
                    for msg in chat_session.messages[:-1]:  # Exclude the current user message
                        if msg.role == "user":
                            # For historical messages, use question as-is (no web search)
                            conversation_history.append({"role": "user", "parts": [msg.text]})
                        elif msg.role == "bot":
                            conversation_history.append({"role": "model", "parts": [msg.text]})
            except Exception as e:
                # If can't load history, continue with single turn
                pass
        
        # Add current question to conversation (web context will be in system instruction)
        conversation_history.append({"role": "user", "parts": [current_question]})
        
        # Build system instruction with web context if available
        system_instruction_text = SYSTEM_INSTRUCTION
        if web_sources:
            context = ""
            for source in web_sources:
                context += f"{source['text']}\n\n" + 100 * '-' + "\n\n"
            system_instruction_text += f"\n\nThông tin tham khảo:\n{context}"
        
        # Tạo model instance với system instruction (bao gồm web context)
        model = genai.GenerativeModel(
            info["model_id"],
            system_instruction=system_instruction_text
        )
        
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