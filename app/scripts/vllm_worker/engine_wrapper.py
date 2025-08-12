from vllm import SamplingParams, AsyncLLMEngine
from vllm.outputs import RequestOutput
from vllm.utils import random_uuid
from vllm.distributed import cleanup_dist_env_and_memory
from vllm.lora.request import LoRARequest
import gc
import torch
from typing import AsyncGenerator
import os
import psutil
# import torch.distributed as dist

from .vllm_config import Config
class AsyncLLMEngineWrapper:
    def __init__(self) -> None:
        self.loaded = False
        self.reap_wait_time = 5
    def _reap_children(self):
        parent = psutil.Process(os.getpid())
        for child in parent.children(recursive=True):
            try:
                child.wait(timeout=5)
            except psutil.TimeoutExpired:
                child.kill()
                child.wait()
    def shutdown(self):
        if self.loaded:
            del self.engine.engine # model_executor.shutdown() happened here
            self._reap_children()
            self.engine.shutdown_background_loop()
            del self.engine # Terminat event loop
            cleanup_dist_env_and_memory()
            gc.collect()
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            self.loaded = False
    def init(self, model_id: str):
        if not self.loaded:
            self.loaded = True
            vllm_config = Config.get_vllm(model_id)
            self.engine = AsyncLLMEngine.from_vllm_config(vllm_config)
    def generate(self, prompt: str, sampling_params: SamplingParams, lora_request: LoRARequest | None) -> AsyncGenerator[RequestOutput, None]:
        if self.engine is None:
            raise Exception("Not initialized")
        return self.engine.generate(
            prompt=prompt,
            sampling_params=sampling_params,
            request_id=random_uuid(),
            lora_request=lora_request
        )