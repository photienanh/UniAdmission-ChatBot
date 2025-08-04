from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
import os
from .schema import NO_CACHE_HEADERS

router = APIRouter()

@router.get("/script/{filename}", name="static", response_class=FileResponse)
async def get_static(filename: str):
    response = FileResponse(os.path.join("scripts", filename))
    response.headers.update(NO_CACHE_HEADERS)
    return response