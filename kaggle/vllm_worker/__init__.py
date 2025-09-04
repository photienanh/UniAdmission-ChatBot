#!ip a

def set_env():
    import os
    from .logging_config import setup_logging
    
    # Network configuration
    os.environ["GLOO_SOCKET_NAME"] = "eth0"
    os.environ["NCCL_SOCKET_NAME"] = "eth0"
    os.environ["VLLM_HOST_IP"] = "127.0.0.1" # Internal ip for data communicate between VLLM components
    os.environ["VLLM_USE_V1"] = "0" # T4 have compute capacity of 7.5, it need at least 8.0 to use V1
    
    # Thiết lập logging để tắt các log INFO không cần thiết
    setup_logging()
    
def prepare(path: str = "/kaggle/working"):
    set_env()
    import shutil, os
    from_path = os.path.join(path, "vllm_worker", "vllm_runner.py")
    to_path = os.path.join(path, "vllm_runner.py")
    shutil.copy(from_path, to_path)