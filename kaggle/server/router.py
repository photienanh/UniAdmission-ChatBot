from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse
from typing import Callable, Awaitable, AsyncGenerator

from .schema import KaggleServerInfo, KaggleRequest, ModelPreOutput, KagglePreInferenceResponse

router = APIRouter()

@router.get("/heath")
async def heath_check(request: Request):
    return Response(status_code=200, content="ok")

@router.get("/info")
async def info(request: Request) -> KaggleServerInfo:
    info: KaggleServerInfo = request.app.state.info
    return info

@router.post("/pre_inference")
async def pre_inference(request: Request, data: KaggleRequest) -> KagglePreInferenceResponse:
    pre_inference_call: Callable[[KaggleRequest], Awaitable[ModelPreOutput]] = request.app.state.pre_inference
    info: KaggleServerInfo = request.app.state.info
    pre_output = await pre_inference_call(data)
    return {
        "info": info,
        "pre_output": pre_output
    }

@router.post("/inference/{stream_id}")
async def inference(request: Request, stream_id: str):
    inference:  Callable[[str], Awaitable[AsyncGenerator[str, None]]] = request.app.state.inference
    generator = await inference(stream_id)
    return StreamingResponse(generator)

