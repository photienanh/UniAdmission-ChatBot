from fastapi import APIRouter, Request, Response
import traceback

from core.types import ModelInfo, KaggleServerInfo
from backend.llm import ModelManager, KaggleManager

router = APIRouter()

@router.get("/models")
async def get_models(request: Request) -> list[ModelInfo]:
    return await ModelManager.get_models()

@router.post("/kaggle")
async def kaggle_init(request: Request, data: KaggleServerInfo):
    try:
        KaggleManager.update_server(data)
        return Response(status_code=200, content="OK")
    except Exception as e:
        traceback.print_exc()
        return Response(status_code=500, content=str(e))

@router.get("/api/cache/search")
async def api_search_from_database(school_id: str, section: str):
    """API endpoint để Kaggle có thể truy cập cache"""
    from backend.llm.database_search import search_from_database
    
    results = search_from_database(school_id, section)
    
    # Convert documents thành format JSON-serializable
    return {
        "school_id": school_id,
        "section": section,
        "documents": [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            } for doc in results
        ],
        "count": len(results)
    }

@router.get("/api/cache/all-docs")
async def api_get_all_cached_docs():
    """Lấy tất cả cached documents"""
    from backend.llm.vector_cache import get_vector_cache
    
    cache = get_vector_cache()
    if not cache or not cache.is_cache_ready():
        return {"documents": [], "ready": False}
    
    all_docs = cache.get_cached_docs()
    return {
        "documents": [
            {
                "content": doc.page_content,
                "metadata": doc.metadata
            } for doc in all_docs
        ],
        "count": len(all_docs),
        "ready": True
    }

@router.get("/api/cache/status")
async def api_cache_status():
    """Kiểm tra trạng thái vector cache"""
    from backend.llm.vector_cache import get_vector_cache
    
    cache = get_vector_cache()
    if not cache:
        return {"ready": False, "message": "Cache not initialized"}
    
    is_ready = cache.is_cache_ready()
    doc_count = len(cache.get_cached_docs()) if is_ready else 0
    
    return {
        "ready": is_ready,
        "document_count": doc_count,
        "message": "Cache ready" if is_ready else "Cache not ready"
    }