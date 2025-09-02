from fastapi import APIRouter, Request, Response, HTTPException
import traceback

from core.types import ModelInfo, KaggleServerInfo
from backend.llm import ModelManager, KaggleManager

router = APIRouter()

# Import AdminManager để check server permissions
from .admin import AdminManager

@router.get("/models")
async def get_models(request: Request) -> list[ModelInfo]:
    return await ModelManager.get_models()

@router.post("/kaggle")
async def kaggle_init(request: Request, data: KaggleServerInfo):
    try:
        server_id = data.get("server_id")
        
        # Check if server is approved
        if server_id and not AdminManager.is_server_approved(server_id):
            raise HTTPException(
                status_code=403, 
                detail=f"Server {server_id} is not approved. Please contact admin for approval."
            )
        
        # Check if server is blocked
        if server_id and AdminManager.is_server_blocked(server_id):
            raise HTTPException(
                status_code=403, 
                detail=f"Server {server_id} is blocked from accessing this system."
            )
        
        KaggleManager.update_server(data)
        return Response(status_code=200, content="OK")
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        traceback.print_exc()
        return Response(status_code=500, content=str(e))