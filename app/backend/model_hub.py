from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from config import GEMINI_MODEL
from .schema import *
from .utility import ModelHub

router = APIRouter()
hub = ModelHub()

@router.post("/request")
async def request_distributer(request: Request, info: ClientInfo):
    request_data = hub.get_request(info)
    return JSONResponse(request_data or {})
@router.post("/response")
async def response_submitter(request: Request, data: ResponseData):
    hub.set_response(data["client"], data)
    return Response(status_code=200)
@router.post("/error")
async def failed_response_submitter(request: Request, data: ErrorData):
    hub.set_error(data["client"], data)
    return Response(status_code=200)
@router.get("/models")
async def get_model_list(request: Request) -> list[ModelInfo]:
    result = hub.get_alive_list()
    result.append({
        "name": "Gemini (API)",
        "id": GEMINI_MODEL,
        "params_size": "Unknown"
    })
    return result
@router.post("/model_test")
async def model_test(request: Request, data: ModelInput):
    return JSONResponse(await hub.inference(data))

async def inference(data: ModelInput) -> ModelOutput:
    result = await hub.inference(data)
    if isinstance(result, dict):
        return result
    else:
        raise Exception(f"Inference error: {result}")