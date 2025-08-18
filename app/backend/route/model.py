from fastapi import APIRouter, Request

from core.types import ModelInfo
from backend.llm import ModelManager

router = APIRouter()

@router.get("/models")
async def get_models(request: Request) -> list[ModelInfo]:
    return ModelManager.get_models()
