from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
import tarfile
import io

from .utils import NO_CACHE_HEADERS
from config import STATIC_DB_PATH, WORKER_ENV_PATH

# Script provider route for kaggle
router = APIRouter()

@router.get("/package/lora/{model_name}", response_class=StreamingResponse)
async def get_lora_model(model_name: str, background_tasks: BackgroundTasks):
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
        tar.add(f"package/lora/{model_name}", arcname='')
    tar_buffer.seek(0)    
    background_tasks.add_task(tar_buffer.close)
    response = StreamingResponse(
        content=tar_buffer, 
        media_type="application/x-tar"
    )
    response.headers.update(NO_CACHE_HEADERS)
    return response

@router.get("/package/static.pkl", response_class=FileResponse)
async def get_static_db():
    return FileResponse(path=STATIC_DB_PATH)

@router.get("/package/worker.env", response_class=FileResponse)
async def get_worker_env():
    return FileResponse(path=WORKER_ENV_PATH)

@router.get("/package/school_name.json", response_class=FileResponse)
async def get_school_name():
    return FileResponse(path="package/school_name.json")

@router.get("/package_multi/{package_name}", response_class=StreamingResponse)
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

@router.get("/package/{package_name}", response_class=StreamingResponse)
async def get_kaggle_dedicated_client(package_name: str, background_tasks: BackgroundTasks):
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
        tar.add(f"../kaggle_dedicated/{package_name}", arcname='')
    tar_buffer.seek(0)    
    background_tasks.add_task(tar_buffer.close)
    response = StreamingResponse(
        content=tar_buffer, 
        media_type="application/x-tar"
    )
    response.headers.update(NO_CACHE_HEADERS)
    return response

