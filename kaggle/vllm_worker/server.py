from vllm import SamplingParams
from vllm.lora.request import LoRARequest
from typing import AsyncGenerator
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response, StreamingResponse
from vllm.entrypoints.utils import with_cancellation
from vllm.utils import set_ulimit
import asyncio
import json
import traceback
from typing import Any
import vllm.envs as envs
import msgspec

from .engine_wrapper import AsyncLLMEngineWrapper
from .server_setup import serve_http

app = FastAPI()
engine = AsyncLLMEngineWrapper()

@app.get("/health")
async def health() -> Response:
    """Health check"""
    return Response(200)
@app.post("/init")
async def initialize_engine(request_dict: dict, raw_request: Request):
    if not engine.loaded:
        try:
            model_id = request_dict["model_id"]
            engine.init(model_id)
            return Response(status_code=200, content="Sucess")
        except Exception as e:
            print(e)
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))
    else:
        return Response(status_code=400, content="Aldready initialized")
@app.post("/generate")
async def generate(request: Request) -> Response:
    """Generate completion for the request.

    The request should be a JSON object with the following fields:
    - prompt: the prompt to use for the generation.
    - stream: whether to stream the results or not.
    - other fields: the sampling parameters (See `SamplingParams` for details).
    """
    try:
        request_dict = await request.json()
        return await _generate(request_dict, request)
    except Exception as e:
        print(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
@with_cancellation # This need raw_request argument
async def _generate(request_dict: dict, raw_request: Request) -> StreamingResponse:
    prompt = request_dict.pop("prompt")
    lora_request = None
    sampling_params = None
    if "lora" in request_dict:
        lora_request = LoRARequest(**request_dict.pop("lora"))
    sampling_params = msgspec.convert(request_dict.pop("params"), type=SamplingParams)
    if not sampling_params.extra_args:
        sampling_params.extra_args = {}
    history = request_dict.pop("history", None)
    results_generator = None
    if history:
        # Map history to OpenAI-style chat messages
        messages = []
        for m in history:
            role = m.get("role", "user")
            # normalize roles: DB/backend may send "bot"
            if role == "bot":
                role = "assistant"
            elif role not in ("user", "assistant"):
                role = "user"
            messages.append({"role": role, "content": m.get("content", "")})
        # append current user prompt as the latest turn
        messages.append({"role": "user", "content": prompt})
        # Use full chat API for multi-turn
        results_generator = await engine.chat(messages=messages, sampling_params=sampling_params, lora_request=lora_request)
    else:
        # Single-turn fallback
        results_generator = await engine.chat_quick(prompt, sampling_params, lora_request)
    # Streaming case
    async def stream_results() -> AsyncGenerator[str, None]:
        last_length = 0
        async for request_output in results_generator:
            text = request_output.outputs[0].text
            yield text[last_length:]
            last_length = len(text)
    return StreamingResponse(stream_results())


async def run_server(**uvicorn_kwargs: Any):
    global app, engine
    set_ulimit()
    app.state.engine_client = engine
    (server, logger) = await serve_http(
        app,
        log_level = "info",
        timeout_keep_alive = envs.VLLM_HTTP_TIMEOUT_KEEP_ALIVE,
        **uvicorn_kwargs
    )
    logger.info("[SUB] Shutting down ...")
    server.should_exit = True
    await server.shutdown()
    logger.info("[SUB] Shutting down ..")
    delattr(app.state, "engine_client")
    engine.shutdown()
    logger.info("[SUB] Shutting down .")
    print("[SUB] Shutdown completed")