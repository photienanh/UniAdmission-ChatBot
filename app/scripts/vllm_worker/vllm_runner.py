import argparse  
import asyncio
import os
from vllm_worker.server import run_server
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    kwargs = vars(args)
    asyncio.run(run_server(**kwargs))
    os._exit(0)