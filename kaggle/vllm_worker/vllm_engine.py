from aiohttp.client import ClientSession
import asyncio
from typing import TypedDict, Optional, AsyncGenerator, Callable

from .vllm_controller import VLLMController
class VLLMJobInfo(TypedDict):
    model_id: str
    message: str
    lora_request: Optional[dict]
    sampling_params: dict
    history: Optional[list[dict]]
class VLLMEngine:
    def __init__(self, on_model_active: Callable[[str], None]) -> None:
        self.controller = VLLMController()
        self.job_queue: list[VLLMJobInfo] = []
        self.current_model_id = ""
        self.busy = False
        self.job_poll = 0.1
        self.busy_poll = 0.1
        self.on_model_active = on_model_active
    async def delete(self):
        await self.controller._unload()
    def _available(self, info: VLLMJobInfo):
        # If current loaded model match, allow job to process
        if self.current_model_id == info["model_id"]:
            return True
            
        # If current loaded model does not match, check if all job with current model is finished
        model_ids = []
        for info_ in self.job_queue:
            model_ids.append(info_["model_id"])
        if self.current_model_id not in model_ids:
            # All current model job is done
            return True
        
        # Other job with current loaded model still in queue:
        return False
    async def _process_request(self, info: VLLMJobInfo) -> AsyncGenerator[str, None]:
        while self.controller.busy:
            await asyncio.sleep(self.busy_poll)
        if self.current_model_id != info["model_id"]:
            self.current_model_id = info["model_id"]
            self.on_model_active(info["model_id"])
            await self.controller.load(info["model_id"])
        url = await self.controller.get_url()
        payload = {
            "prompt": info["message"],
            "params": info["sampling_params"],
        }
        if info.get("history"):
            payload["history"] = info["history"]
        if info["lora_request"] != None:
            payload["lora"] = info["lora_request"]
            
        async with ClientSession() as session:
            async with session.post(f"{url}/generate", json=payload) as response:
                if response.ok:
                    async for chunk in response.content.iter_any():
                        yield chunk.decode("utf-8")
    async def process(self, info: VLLMJobInfo) -> AsyncGenerator[str, None]:
        self.job_queue.append(info)
        while True:
            if self._available(info):# and not self.busy:
                # Forward request to server and wait for result
                # self.busy = True # Do not need to keep busy because server aldready handle it
                result = self._process_request(info)
                # Only pop when Job is completed
                for index, info_ in enumerate(self.job_queue): 
                    if info == info_:
                        self.job_queue.pop(index)
                        break
                # self.busy = False
                return result
            # Await for all jobs with current model id completed
            await asyncio.sleep(self.job_poll)