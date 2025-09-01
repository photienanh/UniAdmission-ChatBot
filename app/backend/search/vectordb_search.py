from ..cache.vector_cache import get_vector_cache

def documents_search(school_id, section):
    # Lấy cached documents
    cache = get_vector_cache()
    if not cache or not cache.is_cache_ready():
        return None
    
    all_docs = cache.get_cached_docs()
    
    # Filter by school_id
    school_docs = [doc for doc in all_docs if doc.metadata.get("school_id") == school_id]
    
    if school_docs:
        # Filter by section
        filtered_docs = [doc for doc in school_docs if doc.metadata.get("section") == section]
    else:
        filtered_docs = None
        
    return filtered_docs

def search_from_vector_db(keywords):
    """Tìm kiếm từ vector database với danh sách keywords"""
    try:
        results = []
        
        for kw in keywords:
            school_id = kw.get("school_id")
            section = kw.get("section")
            if school_id and section:
                docs = documents_search(school_id, section)
                
                if docs:
                    content = "\n\n".join([doc.page_content for doc in docs])
                    description = content[:200] + "..." if len(content) > 200 else content
                    
                    # Tạo title có tên trường để phân biệt
                    title = f"Tìm trường ĐH-CĐ - Cốc Cốc ({school_id})"
                    
                    results.append({
                        "url": "https://hoctap.coccoc.com/tim-truong-dh-cd",
                        "title": title,
                        "description": description,
                        "text": content,
                        "source": "vector_db"
                    })
                else:
                    return None
        
        return results
    except Exception as e:
        return None