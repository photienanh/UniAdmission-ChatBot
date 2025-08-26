from .vector_cache import get_vector_cache

def search_from_database(school_id, section):
    # Lấy cached documents
    cache = get_vector_cache()
    if not cache or not cache.is_cache_ready():
        return []
    
    all_docs = cache.get_cached_docs()
    
    # Filter by school_id
    school_docs = [doc for doc in all_docs if doc.metadata.get("school_id") == school_id]
    
    if school_docs:
        # Filter by section
        filtered_docs = [doc for doc in school_docs if doc.metadata.get("section") == section]
    else:
        filtered_docs = []
        
    return filtered_docs
