from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from .support import ProviderHub
import uuid
from config import SERVICE_REGISTER_TOKEN, GEMINI_MODEL
import json
from typing import Any
import json
from .schema import ModelInfo, NO_CACHE_HEADERS

provider_hub = ProviderHub()
router = APIRouter()

async def direct_consume(client_type: str, data: Any):
    if isinstance(data, str):
        text = data
    else:
        text = json.dumps(data)
    request_id = str(uuid.uuid4())
    result = await provider_hub.consume(client_type, request_id, text)
    if result == None:
        return None
    if isinstance(result, Exception):
        raise result
    return json.loads(result)

@router.websocket("/provider")
async def websocket_provider_register(websocket: WebSocket):
    query_params = websocket.query_params
    client_type = query_params.get("client_type", None)
    name = query_params.get("name", None)
    uid = query_params.get("uid", None)
    access_token = query_params.get("token", None)
    if client_type and name and uid and access_token and access_token == SERVICE_REGISTER_TOKEN:
        await websocket.accept()
        await provider_hub.register_provider(websocket, client_type, name, uid)
        try:
            while True:
                msg = await websocket.receive_json()
                if isinstance(msg, dict):
                    request_id = str(msg.get("request_id"))
                    text = msg.get("text")
                    if not isinstance(text, str):
                        text = json.dumps(text)
                    if request_id and text:
                        await provider_hub.provide(client_type, request_id, text)
        except WebSocketDisconnect:
            print(f"Provider {client_type} disconnect")
            await provider_hub.on_provider_ws_closed(client_type, uid)
    else:
        await websocket.close(code=1008, reason="Invalid query")

@router.websocket("/consumer")
async def websocket_consumer_register(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            msg = await websocket.receive_json()
            if isinstance(msg, dict):
                client_type = msg.get("client_type", None)
                request_id = str(msg.get("request_id", None))
                text = msg.get("text", None)
                if client_type and request_id and text:
                    if not isinstance(text, str):
                        text = json.dumps(text)
                    result = await provider_hub.consume(client_type, request_id, text)
                    await websocket.send_json({
                        "request_id": request_id,
                        "text": result
                    })
    except WebSocketDisconnect:
        print("Consumer disconnected") 
 
@router.post("/consume/{client_type}")
async def restful_consume(request: Request, client_type: str):
    text = await request.body()
    request_id = str(uuid.uuid4())
    result = await provider_hub.consume(client_type, request_id, text.decode())
    if isinstance(result, str):
        return PlainTextResponse(result)
    elif result != None:
        return HTTPException(status_code=500, detail=str(result))
    else:
        return HTTPException(status_code=400, detail="Provider not registed")

@router.get("/models")
async def get_model_list(request: Request) -> list[ModelInfo]:
    infos = provider_hub.get_current_infos()
    infos.append(
        {
            "name": "Gemini",
            "model_type": GEMINI_MODEL
        }
    )
    response = JSONResponse(content=infos)
    response.headers.update(NO_CACHE_HEADERS)
    return response #type:ignore