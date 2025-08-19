from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from config import JWT_SECRET_KEY
from .route import (
    CacheControledStaticFiles,
    template_router,
    auth_router,
    chat_router,
    script_router,
    kaggle_router
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
app.include_router(script_router, tags=["Script"])
app.include_router(kaggle_router, tags=["Kaggle"])
