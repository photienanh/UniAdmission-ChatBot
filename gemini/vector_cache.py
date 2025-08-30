import asyncio
import time
from typing import Optional
from pathlib import Path
import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# Default vector index path - absolute path
VECTOR_INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "vector_database", "vectordb")

def load_model_embedding():
    """Load HuggingFace embedding model"""
    return HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-small")

def load_database(index_path, embedding_model):
    """Load FAISS vector database"""
    vectorstore = FAISS.load_local(index_path, embedding_model, allow_dangerous_deserialization=True)
    all_docs = list(vectorstore.docstore._dict.values())
    return all_docs

class VectorDatabaseCache:
    """
    Vector Database Cache Manager với auto-refresh mỗi 15 phút
    """
    
    def __init__(self, index_path: str, refresh_interval: int = 900):  # 15 minutes = 900 seconds
        self.index_path = Path(index_path)
        self.refresh_interval = refresh_interval
        self.embedding_model = None
        self.cached_docs = None
        self.last_refresh_time = 0
        self._refresh_task = None
        self._is_running = False
        
    async def start(self):
        """Khởi động cache manager"""
        if self._is_running:
            return
                    
        # Load embedding model
        try:
            self.embedding_model = load_model_embedding()
        except Exception as e:
            return
            
        # Initial load
        await self.refresh_cache()
        
        # Start background refresh task
        self._is_running = True
        self._refresh_task = asyncio.create_task(self.background_refresh())
        
    async def stop(self):
        """Dừng cache manager"""
        if not self._is_running:
            return
            
        self._is_running = False
        
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
                
        
    async def refresh_cache(self):
        """Refresh cache từ database"""
        try:
            if not self.index_path.exists():
                return
                
            start_time = time.time()
            
            # Load documents from vector database
            all_docs = load_database(str(self.index_path), self.embedding_model)
            
            # Cache the documents
            self.cached_docs = all_docs
            self.last_refresh_time = time.time()
                        
        except Exception as e:
            pass
            
    async def background_refresh(self):
        """Background task để refresh cache định kỳ"""
        while self._is_running:
            try:
                await asyncio.sleep(self.refresh_interval)
                if self._is_running:
                    await self.refresh_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                pass
                
    def get_cached_docs(self) -> Optional[list]:
        """Lấy cached documents"""
        return self.cached_docs
        
    def is_cache_ready(self) -> bool:
        """Kiểm tra xem cache đã sẵn sàng chưa"""
        return self.cached_docs is not None

# Global cache instance
vector_cache: Optional[VectorDatabaseCache] = None

def get_vector_cache() -> Optional[VectorDatabaseCache]:
    """Get global vector cache instance"""
    return vector_cache

# Cache manager for app lifespan
class VectorCacheManager:
    """Manager for vector cache lifecycle"""
    
    def __init__(self):
        self.cache: Optional[VectorDatabaseCache] = None
    
    async def startup(self, index_path: str = VECTOR_INDEX_PATH, refresh_interval: int = 900):
        """Startup vector cache"""
        try:
            self.cache = VectorDatabaseCache(index_path, refresh_interval)
            await self.cache.start()
            
            # Set global cache instance
            global vector_cache
            vector_cache = self.cache
            
        except Exception as e:
            pass
    
    async def shutdown(self):
        """Shutdown vector cache"""
        try:
            if self.cache:
                await self.cache.stop()
                
            # Clear global cache instance
            global vector_cache
            vector_cache = None
            
        except Exception as e:
            pass

# Global cache manager instance
vector_cache_manager = VectorCacheManager()
