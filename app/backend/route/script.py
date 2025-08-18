from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
import os
import tarfile
import io
from .utils import NO_CACHE_HEADERS

router = APIRouter()

@router.get("/script/{package_name}", response_class=StreamingResponse)
async def get_kaggle_client(package_name: str, background_tasks: BackgroundTasks):
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
        tar.add(f"../kaggle/{package_name}", arcname='')
    tar_buffer.seek(0)    
    background_tasks.add_task(tar_buffer.close)
    response = StreamingResponse(
        content=tar_buffer, 
        media_type="application/x-tar"
    )
    response.headers.update(NO_CACHE_HEADERS)
    return response