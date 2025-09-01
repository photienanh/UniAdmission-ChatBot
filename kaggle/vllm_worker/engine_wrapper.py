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


# Wrapper bao quanh AsyncLLMEngine của vLLM để:
# - Quản lý vòng đời (init, shutdown)
# - Cung cấp API generate và chat tiện lợi
class AsyncLLMEngineWrapper:
    def __init__(self) -> None:
        self.loaded = False             # Đánh dấu model đã load hay chưa
        self.reap_wait_time = 5         # Timeout khi đợi process con dừng

    def _reap_children(self):
        # Thu dọn các process con (worker GPU, subprocesses) còn sót lại
        parent = psutil.Process(os.getpid())
        for child in parent.children(recursive=True):
            try:
                child.wait(timeout=5)   # chờ nó kết thúc
            except psutil.TimeoutExpired:
                child.kill()            # nếu quá thời gian thì kill
                child.wait()

    def shutdown(self):
        # Shutdown engine và thu hồi tài nguyên GPU/CPU
        if self.loaded:
            # Xóa engine bên trong (model_executor.shutdown() được gọi ở đây)
            del self.engine.engine
            self._reap_children()
            # Shutdown event loop nội bộ của AsyncLLMEngine
            self.engine.shutdown_background_loop()
            del self.engine
            # Cleanup các biến môi trường distributed + dọn rác
            cleanup_dist_env_and_memory()
            gc.collect()
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            self.loaded = False

    def init(self, model_id: str):
        # Load model vào GPU bằng AsyncLLMEngine
        if not self.loaded:
            self.loaded = True
            vllm_config = Config.get_vllm(model_id)          # Lấy config (từ vllm_config.py)
            self.engine = AsyncLLMEngine.from_vllm_config(vllm_config)

    def generate(
        self, 
        prompt: str | TokensPrompt, 
        sampling_params: SamplingParams, 
        lora_request: LoRARequest | None
    ) -> AsyncGenerator[RequestOutput, None]:
        # Sinh output từ một prompt (chuỗi hoặc tokenized prompt)
        if self.engine is None:
            raise Exception("Not initialized")
        return self.engine.generate(
            prompt=prompt,
            sampling_params=sampling_params,
            request_id=random_uuid(),      # request_id duy nhất cho mỗi job
            lora_request=lora_request      # nếu có LoRA thì kèm theo
        )

    async def chat_quick(
        self, 
        prompt: str, 
        sampling_params: SamplingParams, 
        lora_request: LoRARequest | None
    ):
        # Chat nhanh: chỉ 1 câu user input, không có history
        messages = [ChatCompletionUserMessageParam(content=prompt, role="user")]
        return await self.chat(
            messages=messages,
            sampling_params=sampling_params,
            lora_request=lora_request,
            chat_template_kwargs={
                "enable_thinking": False   # tắt "thinking" mode (nếu model hỗ trợ)
            }
        )

    async def chat(
        self,
        messages: list[ChatCompletionMessageParam],          # Danh sách message (user/assistant/system)
        sampling_params: SamplingParams,                    # Tham số sampling (temperature, top_p,...)
        lora_request: LoRARequest | None,                   # LoRA adapter (nếu có)
        chat_template_content_format: ChatTemplateContentFormatOption = "auto",
        chat_template: Optional[str] = None,
        add_generation_prompt: bool = True,
        continue_final_message: bool = False,
        chat_template_kwargs: Optional[dict[str, Any]] = None
    ):
        # Hàm chat đầy đủ, hỗ trợ multi-turn conversation
        if self.engine is None: 
            raise Exception("Model not loaded")

        # Lấy tokenizer tương ứng với model hiện tại
        tokenizer = await self.engine.get_tokenizer(lora_request)
        model_config = self.engine.engine.get_model_config()

        # Xác định cách format message dựa trên template & config
        resolved_content_format = resolve_chat_template_content_format(
            chat_template,
            None,
            chat_template_content_format,
            tokenizer,
            model_config=model_config,
        )

        # Build kwargs cho chat template
        _chat_template_kwargs: dict[str, Any] = dict(
            chat_template=chat_template,
            add_generation_prompt=add_generation_prompt,
            continue_final_message=continue_final_message,
            tools=None,
        )
        _chat_template_kwargs.update(chat_template_kwargs or {})

        # Parse message list thành conversation object để dễ xử lý
        conversation, _ = parse_chat_messages(
            messages, 
            model_config,
            tokenizer,
            content_format=resolved_content_format,
        )

        # Nếu model dùng MistralTokenizer → dùng template riêng
        if isinstance(tokenizer, MistralTokenizer):
            prompt_token_ids = apply_mistral_chat_template(
                tokenizer,
                messages=messages,  # type: ignore
                **_chat_template_kwargs,
            )
        else:
            # Với model thường (HF), build string từ conversation rồi encode
            prompt_str = apply_hf_chat_template(
                tokenizer=tokenizer, 
                conversation=conversation,
                model_config=model_config,
                **_chat_template_kwargs,
            )
            prompt_token_ids = tokenizer.encode(prompt_str, add_special_tokens=False)

        # Tạo TokensPrompt từ prompt_token_ids
        prompt = TokensPrompt(prompt_token_ids=prompt_token_ids)

        # Cuối cùng gọi generate
        return self.generate(
            prompt,
            sampling_params=sampling_params,
            lora_request=lora_request,
        )
