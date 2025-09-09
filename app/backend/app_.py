from fastapi import FastAPI, Request
import logging
from starlette.middleware.sessions import SessionMiddleware
from config import JWT_SECRET_KEY
from .route import (
    CacheControledStaticFiles,
    template_router,
    auth_router,
    chat_router,
    package_router,
    worker_router
)

from database import init_db, close_db

# App lifespan
from contextlib import asynccontextmanager
from fastapi import FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    
    yield # Return control to FastAPI app
    
    # Shutdown
    await close_db()

app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=JWT_SECRET_KEY)
app.mount("/static", CacheControledStaticFiles(directory="frontend/static"), name="static")
app.include_router(template_router, tags=["JinjaTemplate"])
app.include_router(auth_router, tags=["Authentication"])
app.include_router(chat_router, tags=["Chat"])
app.include_router(package_router, tags=["Package"])
app.include_router(worker_router, tags=["Kaggle"])

# Logging
uvicorn_access = logging.getLogger("uvicorn.access")
@app.middleware("http")
async def silient_worker_ping(request: Request, call_next):
    path = request.url.path
    if path in ["/worker/register"]:
        uvicorn_access.disabled = True
    else:
        uvicorn_access.disabled = False
    return await call_next(request)