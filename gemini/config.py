import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Tắt INFO, WARNING, ERROR logs
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Tắt oneDNN warnings

import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# Import và config TensorFlow để tắt tất cả warnings
try:
    import tensorflow as tf #type:ignore
    tf.get_logger().setLevel('ERROR')
    tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
except ImportError:
    pass  # TensorFlow not installed


# Get API keys from environment variables
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# System instruction for Gemini
SYSTEM_INSTRUCTION = "Bạn là một AI tư vấn tuyển sinh đại học chuyên nghiệp. Hãy trả lời các câu hỏi một cách chính xác, hữu ích và thân thiện. Có thể sử dụng những thông tin được cung cấp để đưa ra câu trả lời hoặc lời khuyên tốt nhất."


# Web Search Config
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
GPT_API_KEY = os.getenv("GPT_API_KEY")
