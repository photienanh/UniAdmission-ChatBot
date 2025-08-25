import os

# Set environment variables directly
os.environ["IS_DEVELOPMENT"] = "True"
os.environ["JWT_DURATION"] = str(60 * 60)
os.environ["GEMINI_API_KEY"] = "AIzaSyDaQWFtNjn_kD_N6ZdklJQhQMZfY4krv-8"
os.environ["BRAVE_API_KEY"] = "BSAqc_JfqRcQCwHzNL3G2Y7p6XBWbhC"
os.environ["GPT_API_KEY"] = "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"

GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Web Search Config
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
GPT_API_KEY = os.getenv("GPT_API_KEY")

# System instruction for Gemini
SYSTEM_INSTRUCTION = "Bạn là một AI tư vấn tuyển sinh đại học chuyên nghiệp. Hãy trả lời các câu hỏi một cách chính xác, hữu ích và thân thiện. Có thể sử dụng những thông tin được cung cấp để đưa ra câu trả lời hoặc lời khuyên tốt nhất."