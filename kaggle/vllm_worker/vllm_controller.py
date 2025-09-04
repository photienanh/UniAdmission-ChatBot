import subprocess
from aiohttp.client import ClientSession
import asyncio
import uuid
import psutil
import sys
from typing import Optional
import aiohttp
import time

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
def get_uuid() -> str:
    return str(uuid.uuid4())
class VLLMController:
    def __init__(self) -> None:
        self.port = 8001
        self.p = None
        self.init_poll = 3
        self.kill_poll = 3
        self.busy_poll = 0.1
        self.busy = False
        self.shutdown_timeout = 10
    async def _unload(self):
        if self.p != None:
            self.p.terminate()
            try:
                print(f"[VLLM Controller] Await for process {self.p.pid} to shutdown")
                self.p.wait(self.shutdown_timeout)
                print(f"[VLLM Controller] Process {self.p.pid} terminated")
            except subprocess.TimeoutExpired:
                try:
                    self.p.kill()
                    self.p.wait(self.shutdown_timeout)
                    print(f"[VLLM Controller] Process {self.p.pid} killed")
                except subprocess.TimeoutExpired:
                    print(f"[VLLM Controller] Shutdown timeout")
                    self.p = None
                    return
    async def load(self, model_id: str):
        self.busy = True
        await self._unload()
        
        process = find_process_using_port(self.port)
        while process is not None:
            print(f"[VLLM Controller] Process with port {self.port} still alive, trying to kill")
            process.terminate()
            try:
                process.wait(self.kill_poll)
            except subprocess.TimeoutExpired:
                process.kill()
                process = find_process_using_port(self.port)

        self.p = subprocess.Popen(
            ["python", "vllm_runner.py", "--host=127.0.0.1", f"--port={self.port}"],
            # stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        url = f"http://127.0.0.1:{self.port}"
        payload = {
            "model_id": model_id
        }
        while True:
            try:
                async with ClientSession() as session:
                    async with session.post(f"{url}/init", json=payload) as response:
                        self.busy = False
                        return
            except aiohttp.ClientConnectionError as e:
                await asyncio.sleep(self.init_poll)
    async def get_url(self):
        while self.busy:
            await asyncio.sleep(self.busy_poll)
        return f"http://127.0.0.1:{self.port}"