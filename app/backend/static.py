from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
import os

router = APIRouter()

@router.get("/static/{filename}", name="static", response_class=FileResponse)
async def get_static(filename: str):
    response = FileResponse(os.path.join("static", filename))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response