from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
import os

router = APIRouter()

@router.get("/static/{filename}", name="static", response_class=FileResponse)
async def get_static(filename: str):
    return FileResponse(os.path.join("static", filename))