from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
import tarfile
import io
from .utils import NO_CACHE_HEADERS

router = APIRouter()

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
import tarfile
import io
from .utils import NO_CACHE_HEADERS

router = APIRouter()

# Import AdminManager từ admin router để check permissions
from .admin import AdminManager

@router.get("/script/{package_name}", response_class=StreamingResponse)
async def get_kaggle_client(
    package_name: str, 
    background_tasks: BackgroundTasks,
    server_id: str = Query(..., description="Server ID for permission check")
):
    """Download package với permission check"""
    
    # Check if server is approved to download this package
    if not AdminManager.is_package_allowed(server_id, package_name):
        raise HTTPException(
            status_code=403, 
            detail=f"Server {server_id} not approved to download {package_name}. Please request access through admin."
        )
    
    try:
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating package: {str(e)}")
