import subprocess
from aiohttp.client import ClientSession
import asyncio
import psutil
import sys
from typing import Optional
import aiohttp
import gc
import torch

def find_process_using_port(port: int) -> Optional[psutil.Process]:
    # From vllm lib
    # TODO: We can not check for running processes with network
    # port on macOS. Therefore, we can not have a full graceful shutdown
    # of vLLM. For now, let's not look for processes in this case.
    # Ref: https://www.florianreinhard.de/accessdenied-in-psutil/
    if sys.platform.startswith("darwin"):
        return None
    for conn in psutil.net_connections():
        if conn.laddr.port == port: #type:ignore
            try:
                return psutil.Process(conn.pid)
            except psutil.NoSuchProcess:
                return None
    return None
class VLLMController:
    def __init__(self) -> None:
        self.port = 8000
        self.p = None
        self.init_poll = 3
        self.kill_poll = 3
        self.busy_poll = 0.1
        self.busy = False
        self.shutdown_timeout = 30
    async def _unload(self):
        if self.p != None:
            timeout = self.shutdown_timeout
            while True:
                try:
                    self.p.terminate()
                    print(f"[VLLM Controller] Await for process {self.p.pid} to shutdown")
                except ProcessLookupError:
                    print(f"[VLLM Controller] Process {self.p.pid} terminated")
                    self.p = None
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    gc.collect()
                    return
                except PermissionError:
                    print(f"[VLLM Controller] Permission denied when trying to terminate process {self.p.pid}")
                    raise Exception("[VLLM Controller] FATAL ERROR")
                await asyncio.sleep(self.kill_poll)
                if timeout <= 0:
                    print(f"[VLLM Controller] Shutdown timeout")
                    self.p = None
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    gc.collect()
                    return
                else:
                    timeout -= self.kill_poll
    async def load(self, model_id: str):
        self.busy = True
        await self._unload()
        process = find_process_using_port(self.port)
        while process is not None:
            print(f"[VLLM Controller] process still alive, trying to terminate")
            process.terminate()
            process = find_process_using_port(self.port)
            await asyncio.sleep(self.kill_poll)
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        gc.collect()
        self.p = subprocess.Popen([
            "python", "-m", "vllm.entrypoints.openai.api_server",
            "--model", model_id,
            "--host", "127.0.0.1",
            "--port", str(self.port),
            "--dtype", "float16",
            "--enable-lora",
            "--max-lora-rank", "16",
            "--tensor-parallel-size", "2",
            "--gpu-memory-utilization", "0.9",
            "--max-model-len", "8192",
            # "--enforce-eager"
        ])
        url = f"http://127.0.0.1:{self.port}"
        while True:
            try:
                async with ClientSession() as session:
                    async with session.post(f"{url}/models",) as response:
                        print(f"[VLLM Controller] Server started {response.status}: {await response.text()}")
                        self.busy = False
                        return
            except aiohttp.ClientConnectionError as e:
                print(f"[VLLM Engine] Server is starting: {e}")
                await asyncio.sleep(self.init_poll)
    async def get_url(self):
        while self.busy:
            await asyncio.sleep(self.busy_poll)
        return f"http://127.0.0.1:{self.port}"