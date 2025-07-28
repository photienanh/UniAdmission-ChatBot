# Test module, not used yet

from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from .support import ProviderHub
import uuid
from config import SERVICE_REGISTER_TOKEN
import json

from .schema import ModelInfo

provider_hub = ProviderHub()
router = APIRouter()

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
    return PlainTextResponse(result)

@router.get("/models")
async def get_model_list(request: Request) -> list[ModelInfo]:
    infos = provider_hub.get_current_infos()
    infos.append(
        {
            "name": "Gemini",
            "model_type": "gemini-2.0-flash-lite-preview-02-05"
        }
    )
    return JSONResponse(content=infos) #type:ignore