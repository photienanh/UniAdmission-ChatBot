from fastapi import APIRouter, Request, Response
import traceback

from core.types import ModelInfo, KaggleServerInfo
from backend.llm import ModelManager, KaggleManager

router = APIRouter()

@router.get("/models")
async def get_models(request: Request) -> list[ModelInfo]:
    return ModelManager.get_models()

@router.post("/kaggle")
async def kaggle_init(request: Request, data: KaggleServerInfo):
    try:
        print(f"[Kaggle] {data["domain"]}")
        KaggleManager.update_server(data)
        return Response(status_code=200, content="OK")
    except Exception as e:
        traceback.print_exc()
        return Response(status_code=500, content=str(e))