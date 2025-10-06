from fastapi import APIRouter, Request
from fastapi.responses import Response, StreamingResponse
from typing import Callable, Awaitable, AsyncGenerator

from .schema import WorkerServerInfo, WorkerChatRequest, ModelPreOutput, WorkerPreInferenceResponse
from .protocol import ServerModel

router = APIRouter()

@router.get("/heath")
async def heath_check(request: Request):
    return Response(status_code=200, content="ok")

@router.get("/info")
async def info(request: Request) -> WorkerServerInfo:
    info: WorkerServerInfo = request.app.state.info
    return info

@router.post("/pre_inference")
async def pre_inference(request: Request, data: WorkerChatRequest) -> WorkerPreInferenceResponse:
    model: ServerModel = request.app.state.model
    info: WorkerServerInfo = request.app.state.info
    is_local: bool = request.app.state.is_local
    deploy_url: str | None = request.app.state.deploy_url
    pre_output = await model.pre_inference(data)
    domain = info["domain"]
    if is_local and deploy_url != None:
        domain = deploy_url
    pre_output["result_url"] = f'{domain}/inference/{pre_output["result_url"]}'
    return {
        "info": info,
        "pre_output": pre_output
    }

@router.get("/inference/{stream_id}")
async def inference(request: Request, stream_id: str):
    model: ServerModel = request.app.state.model
    generator = model.inference(stream_id)
    return StreamingResponse(generator)

@router.post("/inference/{stream_id}")
async def inference_post(request: Request, stream_id: str):
    """Bypass ngrok"""
    model: ServerModel = request.app.state.model
    generator = model.inference(stream_id)
    return StreamingResponse(generator)

