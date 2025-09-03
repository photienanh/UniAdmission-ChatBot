import requests
from typing import List, Dict, Any, Optional
import os

class VectorCacheClient:
    """Client để kết nối với vector cache API từ Kaggle"""
    
    def __init__(self, app_domain: str):
        """
        Initialize client với domain của app server
        Args:
            app_domain: Domain của app server (ví dụ: "https://abc123.ngrok.io")
        """
        self.app_domain = app_domain.rstrip('/')
        
    def search_from_database(self, school_id: str, section: str) -> List[Dict[str, Any]]:
        """
        Tìm kiếm documents từ vector cache
        Args:
            school_id: ID của trường (ví dụ: "UET", "HUST", "PTIT")
            section: Section cần tìm ("thong_tin_chung", "diem_chuan", "tuyen_sinh")
        Returns:
            List documents với format chuẩn hóa hoặc empty list nếu không tìm thấy
        """
        try:
            url = f"{self.app_domain}/api/cache/search"
            params = {
                "school_id": school_id,
                "section": section
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            documents = data.get("documents", [])
            
            # Normalize format for notebook compatibility  
            normalized_docs = []
            for doc in documents:
                # Handle both old and new API formats
                if "content" in doc:
                    normalized_docs.append({
                        "content": doc["content"],
                        "metadata": doc.get("metadata", {}),
                        "source": "vector_db"  # Add source identifier for backend
                    })
                elif "page_content" in doc:
                    normalized_docs.append({
                        "content": doc["page_content"], 
                        "metadata": doc.get("metadata", {}),
                        "source": "vector_db"  # Add source identifier for backend
                    })
                else:
                    # Fallback - assume the doc itself is the content
                    normalized_docs.append({
                        "content": str(doc),
                        "metadata": {},
                        "source": "vector_db"  # Add source identifier for backend
                    })
            
            return normalized_docs
            
        except Exception as e:
            print(f"[VectorCache] Error searching cache: {e}")
            return []
    
    def get_all_cached_docs(self) -> Dict[str, Any]:
        """
        Lấy tất cả cached documents
        Returns:
            Dict với keys: documents, count, ready
        """
        try:
            url = f"{self.app_domain}/api/cache/all-docs"
            
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"[VectorCache] Error getting all docs: {e}")
            return {"documents": [], "count": 0, "ready": False}
    
    def batch_search(self, search_queries: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Tìm kiếm batch nhiều queries
        Args:
            search_queries: List of {"school_id": str, "section": str}
        Returns:
            List of all documents found
        """
        all_docs = []
        
        for query in search_queries:
            school_id = query.get("school_id")
            section = query.get("section")
            
            if school_id and section:
                docs = self.search_from_database(school_id, section)
                all_docs.extend(docs)
        
        return all_docs

# Global instance - sẽ được khởi tạo với domain từ config
vector_cache_client: Optional[VectorCacheClient] = None

def initialize_vector_cache_client(app_domain: str):
    """Initialize global vector cache client"""
    global vector_cache_client
    vector_cache_client = VectorCacheClient(app_domain)

def get_vector_cache_client() -> Optional[VectorCacheClient]:
    """Get global vector cache client"""
    return vector_cache_client
