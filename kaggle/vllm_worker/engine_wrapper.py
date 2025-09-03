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
from typing import Optional, Any
# import torch.distributed as dist
from vllm.transformers_utils.tokenizers import MistralTokenizer
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionUserMessageParam
from vllm.entrypoints.chat_utils import (
    ChatTemplateContentFormatOption, 
    resolve_chat_template_content_format, 
    apply_hf_chat_template,
    apply_mistral_chat_template,
    parse_chat_messages
)
from vllm.inputs.data import TokensPrompt

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
    def generate(self, prompt: str | TokensPrompt, sampling_params: SamplingParams, lora_request: LoRARequest | None) -> AsyncGenerator[RequestOutput, None]:
        if self.engine is None:
            raise Exception("Not initialized")
        return self.engine.generate(
            prompt=prompt,
            sampling_params=sampling_params,
            request_id=random_uuid(),
            lora_request=lora_request
        )
    async def chat_quick(
        self, prompt: str, sampling_params: SamplingParams, lora_request: LoRARequest | None
    ):
        messages = [ChatCompletionUserMessageParam(content=prompt, role="user")]
        return await self.chat(
            messages=messages,
            sampling_params=sampling_params,
            lora_request=lora_request,
            chat_template_kwargs={
                "enable_thinking": False
            }
        )
    async def chat(
        self,
        messages: list[ChatCompletionMessageParam],
        sampling_params: SamplingParams,
        lora_request: LoRARequest | None,
        chat_template_content_format: ChatTemplateContentFormatOption = "auto",
        chat_template: Optional[str] = None,
        add_generation_prompt: bool = True,
        continue_final_message: bool = False,
        chat_template_kwargs: Optional[dict[str, Any]] = None
    ):
        if self.engine is None: raise Exception("Model not loaded")
        tokenizer = await self.engine.get_tokenizer(lora_request)
        model_config = self.engine.engine.get_model_config()
        resolved_content_format = resolve_chat_template_content_format(
            chat_template,
            None,
            chat_template_content_format,
            tokenizer,
            model_config=model_config,
        )
        _chat_template_kwargs: dict[str, Any] = dict(
            chat_template=chat_template,
            add_generation_prompt=add_generation_prompt,
            continue_final_message=continue_final_message,
            tools=None,
        )
        _chat_template_kwargs.update(chat_template_kwargs or {})
        conversation, _ = parse_chat_messages(
            messages, #type:ignore
            model_config,
            tokenizer,
            content_format=resolved_content_format,
        )

        if isinstance(tokenizer, MistralTokenizer):
            prompt_token_ids = apply_mistral_chat_template(
                tokenizer,
                messages=messages, #type:ignore
                **_chat_template_kwargs,
            )
        else:
            prompt_str = apply_hf_chat_template(
                tokenizer=tokenizer, #type:ignore
                conversation=conversation,
                model_config=model_config,
                **_chat_template_kwargs,
            )
            prompt_token_ids = tokenizer.encode(prompt_str, add_special_tokens=False)
        prompt = TokensPrompt(prompt_token_ids=prompt_token_ids)
        return self.generate(
            prompt,
            sampling_params=sampling_params,
            lora_request=lora_request,
        )