from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from config import JWT_SECRET_KEY
from .route import (
    CacheControledStaticFiles,
    template_router,
    auth_router,
    chat_router,
    script_router,
    kaggle_router,
    admin_router
)

from database import init_db, close_db

# App lifespan
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .cache.vector_cache import vector_cache_manager, VECTOR_INDEX_PATH
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    
    # Khởi động vector cache với refresh 15 phút
    await vector_cache_manager.startup(
        index_path=VECTOR_INDEX_PATH,
        refresh_interval=900  # 15 phút = 900 giây
    )
    
    yield # Return control to FastAPI app
    
    # Shutdown
    await vector_cache_manager.shutdown()
    await close_db()

app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=JWT_SECRET_KEY)
app.mount("/static", CacheControledStaticFiles(directory="frontend/static"), name="static")
app.include_router(template_router, tags=["JinjaTemplate"])
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat_router, tags=["Chat"])
app.include_router(script_router, tags=["Script"])
app.include_router(kaggle_router, tags=["Kaggle"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
