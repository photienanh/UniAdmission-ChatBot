
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from urllib.parse import urlparse
import os
import asyncio
from contextlib import asynccontextmanager

from config import DATABASE_CONNECTION_POOL_SIZE, DATABASE_URI, DATABASE_ECHO

from database.schema import Base

folder_path = os.path.dirname(urlparse(DATABASE_URI).path.lstrip("/"))
os.makedirs(folder_path, exist_ok=True)

_engine = create_async_engine(
    url=DATABASE_URI,
    connect_args={"check_same_thread": False},
    pool_size=DATABASE_CONNECTION_POOL_SIZE,
    max_overflow = 0,
    echo=DATABASE_ECHO
)
_semaphore = asyncio.Semaphore(DATABASE_CONNECTION_POOL_SIZE)
_AsyncSessionLocal = async_sessionmaker(bind=_engine, autoflush=False, autocommit=False)
async def init_db():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
async def close_db():
    await _engine.dispose()
    
@asynccontextmanager
async def session():
    async with _semaphore:
        async with _AsyncSessionLocal() as session:
            yield session