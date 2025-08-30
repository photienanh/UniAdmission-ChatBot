from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from urllib.parse import urlparse
import os
import asyncio
from contextlib import asynccontextmanager

from config import DATABASE_CONNECTION_POOL_SIZE, DATABASE_URI, DATABASE_ECHO
from database.schema import Base

# Nếu DATABASE_URI là SQLite (ví dụ sqlite+aiosqlite:///./data/chat.db)
# thì cần đảm bảo folder chứa file DB tồn tại
folder_path = os.path.dirname(urlparse(DATABASE_URI).path.lstrip("/"))
os.makedirs(folder_path, exist_ok=True)

# Tạo async engine kết nối database
_engine = create_async_engine(
    url=DATABASE_URI,
    connect_args={"check_same_thread": False},       # SQLite cần tùy chọn này khi chạy async
    pool_size=DATABASE_CONNECTION_POOL_SIZE,         # số kết nối tối đa trong pool
    max_overflow=0,                                  # không cho vượt quá pool_size
    echo=DATABASE_ECHO                               # True thì in log SQL ra console
)

# Semaphore để giới hạn số session đồng thời = pool_size
_semaphore = asyncio.Semaphore(DATABASE_CONNECTION_POOL_SIZE)

# Tạo session factory (async session)
_AsyncSessionLocal = async_sessionmaker(
    bind=_engine,
    autoflush=False,     # không auto flush trước query
    autocommit=False     # phải gọi commit thủ công
)

# Hàm khởi tạo DB: tạo bảng từ Base.metadata (nếu chưa có)
async def init_db():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Hàm đóng DB: giải phóng toàn bộ connection trong pool
async def close_db():
    await _engine.dispose()

# Context manager để mở session làm việc với DB
@asynccontextmanager
async def session():
    async with _semaphore:                     # chặn nếu pool đầy
        async with _AsyncSessionLocal() as session:
            yield session                      # trả về session cho CRUD dùng
            # Khi ra khỏi block, session sẽ tự đóng