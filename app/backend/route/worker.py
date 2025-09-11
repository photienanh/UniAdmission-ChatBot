from fastapi import APIRouter, Response
import traceback

from core.types import ModelInfo, WorkerServerInfo, WorkerStoreChatData
from backend.llm import ModelManager, WorkerManager

router = APIRouter()

@router.get("/models")
async def get_models() -> list[ModelInfo]:
    """Get all available model. Internal use only"""
    return await ModelManager.get_models()

@router.post("/worker/register")
async def kaggle_init(data: WorkerServerInfo):
    """Register kaggle server. Internal use only"""
    try:
        WorkerManager.update_worker(data)
        return Response(status_code=200, content="OK")
    except Exception as e:
        traceback.print_exc()
        return Response(status_code=500, content=str(e))

@router.post("/worker/store_chat")
async def kaggle_store_chat(data: WorkerStoreChatData):
    """Used to update chat on database. Internal use only"""
    await ModelManager.store_chat(
        user_id=data["forward_kwargs"]["user_id"],
        session_id=data["forward_kwargs"]["session_id"],
        user_text=data["forward_kwargs"]["user_text"],
        user_timestamp=data["forward_kwargs"]["user_timestamp"],
        model_output=data["model_output"]
    )
    return Response(status_code=200, content="ok")