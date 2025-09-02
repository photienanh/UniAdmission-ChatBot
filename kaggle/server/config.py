"""Configuration constants for Kaggle deployment"""

from .schema import ModelInfo, ModelStatus, KaggleServerInfo

# Templates and constants
DOC_TEMPLATE = "[**{title}**]({url}):\n{text}\n"
PROMPT_TEMPLATE = """{context_block}\nCâu hỏi:\n{question}\nCâu trả lời:"""
SEP = "$$$"
SOURCE = "kaggle"

# Model configuration
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

LORA_MAPPER = {
    1: {
        "lora_int_id": 1, # Same as key
        "lora_name": "Qwen Adapter v1",
        "lora_path": "/kaggle/input/qwen-lora-adapter/qwen_lora_adapter"
    }
}

PRELOAD_MODEL = "Qwen/Qwen3-4B"

def create_client_info(domain: str = "http://127.0.0.1:8002", server_id: str = None) -> KaggleServerInfo:
    """Create client info with the specified domain and server_id"""
    info = {
        "name": "Testv1",
        "domain": domain,
        "models": MODEL_STATUS
    }
    if server_id:
        info["server_id"] = server_id
    return info

def set_active(model_id: str):
    """Set the active model"""
    print(f"[Global] Switched to model {model_id}")
    if SEP in model_id:
        model_id = model_id.split(SEP)[0]
    for model in MODEL_STATUS:
        if model["id"].startswith(model_id):
            model["active"] = True
            model["scheduled"] = False
        else:
            model["active"] = False
            model["scheduled"] = False
