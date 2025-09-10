import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API keys from environment variables
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Web Search Config
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
GPT_API_KEY = os.getenv("GPT_API_KEY")

# System instruction
SYSTEM_INSTRUCTION = "Bạn là một AI tư vấn tuyển sinh đại học chuyên nghiệp. Hãy trả lời các câu hỏi một cách chính xác, hữu ích và thân thiện. Có thể sử dụng những thông tin được cung cấp để đưa ra câu trả lời hoặc lời khuyên tốt nhất."
GEMINI_SYSTEM_INSTRUCTION = """Bạn là một AI tư vấn tuyển sinh đại học chuyên nghiệp (lưu ý năm hiện tại là 2025). Hãy trả lời các câu hỏi một cách chính xác, hữu ích và thân thiện. Có thể sử dụng những thông tin được cung cấp để đưa ra câu trả lời hoặc lời khuyên tốt nhất. Lưu ý nếu có phần "Thông tin tham khảo:" là do hệ thống cung cấp, người dùng chỉ nhập phần "Câu hỏi:", do đó khi trả lời không dẫn dắt kiểu "dựa trên thông tin bạn cung cấp" hay là "thông tin tham khảo"."""