#!ip a
# Not used
def set_env():
    import os
    os.environ["GLOO_SOCKET_NAME"] = "eth0"
    os.environ["NCCL_SOCKET_NAME"] = "eth0"
    os.environ["VLLM_HOST_IP"] = "127.0.0.1" # Internal ip for data communicate between VLLM components
    os.environ["VLLM_USE_V1"] = "0" # T4 have compute capacity of 7.5, it need at least 8.0 to use V1
    os.environ["VLLM_ATTENTION_BACKEND"] = "XFORMERS"
    
def prepare(path: str = "/kaggle/working"):
    set_env()