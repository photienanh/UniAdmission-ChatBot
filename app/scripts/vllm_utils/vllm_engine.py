from typing import TypedDict
import subprocess
import os
import signal
from aiohttp.client import ClientSession
import asyncio
import uuid
import psutil
import sys
from typing import Optional
import time
import aiohttp
from openai import OpenAI, AsyncOpenAI, AsyncStream
from openai.types import Completion


from .config_parsers import ConfigParser


from .vllm_controller import VLLMController
class JobInfo(TypedDict):
    model_id: str
    message: str
    stream: bool
class JobResult(TypedDict):
    text: list[str]
class VLLMEngine:
    def __init__(self) -> None:
        self.controller = VLLMController()
        self.job_queue: list[JobInfo] = []
        self.current_model_id = ""
        self.busy = False
        self.job_poll = 0.1
        self.busy_poll = 0.1
    def _available(self, info: JobInfo):
        # First call first got, dues to no async

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
    async def _process_request(self, info: JobInfo) -> JobResult:
        while self.controller.busy:
            await asyncio.sleep(self.busy_poll)
        if self.current_model_id != info["model_id"]:
            self.current_model_id = info["model_id"]
            await self.controller.load(info["model_id"])
        url = await self.controller.get_url()
        # payload = {
        #     "prompt": info["message"],
        #     "stream": False,
        #     "temperature": 0.8, 
        #     "top_p": 0.95,
        #     "max_tokens": 128
        # }
        client = AsyncOpenAI(base_url=f"{url}/v1", api_key="EMPTY")
        model = self.current_model_id
        
        completion = await client.completions.create(
            model=model,
            prompt=info["message"],
            echo=False,
            n=2,
            stream=info["stream"],
            logprobs=3
        )
        if isinstance(completion, Completion):
            result = completion.choices[0].text
        else:
            result = ""
            async for c in completion:
                result += c.choices[0].text
        return JobResult(text=[result])
    async def process(self, info: JobInfo) -> JobResult:
        self.job_queue.append(info)
        while True:
            if self._available(info):# and not self.busy:
                # Forward request to server and wait for result
                # self.busy = True # Do not need to keep busy because server aldready handle it
                result = await self._process_request(info)
                # Only pop when Job is completed
                for index, info_ in enumerate(self.job_queue): 
                    if info == info_:
                        self.job_queue.pop(index)
                        break
                # self.busy = False
                return result
            # Await for all jobs with current model id completed
            await asyncio.sleep(self.job_poll)