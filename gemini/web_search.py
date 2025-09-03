import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
from newspaper import Article
from io import StringIO
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from search_router import route_search
from database_search import search_from_database

# Get API keys from environment
BRAVE_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")
def web_search_keywords(keywords, max_results, domain_restrict=False):
    """Tìm kiếm thông tin từ web với danh sách keywords"""
    
    # Check API key
    if not BRAVE_API_KEY:
        return None
        
    try:
        pages = []
        for q in keywords:
            # Brave Search API endpoint
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": BRAVE_API_KEY}
            params = {
                "q": q,
                "count": max_results,
                "search_lang": "vi",  # Vietnamese language
                "safesearch": "moderate",
                "text_decorations": "false",  # Không cần đánh dấu văn bản
            }
            
            response = requests.get(url, headers=headers, params=params)
            time.sleep(1)
        
            if response.status_code != 200:
                continue
                
            data = response.json()
            
            results = data.get("web", {}).get("results", [])

            for result in results[:max_results]:
                title = result.get("title", "")
                description = result.get("description", "")
                url_result = result.get("url", "")
                            
                if title and description:
                    item = {
                        "title": title,
                        "description": description,
                        "url": url_result
                    }
                    pages.append(item)
                
        return pages
    except Exception:
        return None

def search_from_vector_db(vector_keywords):
    """Tìm kiếm từ vector database với danh sách keywords"""
    try:
        vector_results = []
        
        for kw in vector_keywords:
            school_id = kw.get("school_id")
            section = kw.get("section")
            if school_id and section:
                docs = search_from_database(school_id, section)
                
                if docs:
                    combined_content = "\n\n".join([doc.page_content for doc in docs])
                    description = combined_content[:200] + "..." if len(combined_content) > 200 else combined_content
                    
                    # Tạo title có tên trường để phân biệt
                    title = f"Tìm trường ĐH-CĐ - Cốc Cốc ({school_id})"
                    
                    vector_results.append({
                        "title": title,
                        "description": description,
                        "url": "https://hoctap.coccoc.com/tim-truong-dh-cd",
                        "text": combined_content,
                        "source": "vector_db"
                    })
        
        return vector_results
    except Exception as e:
        return []

def unified_search(question, max_results, domain_restrict=False):
    """
    Tìm kiếm thống nhất sử dụng router để quyết định nguồn
    
    Returns:
        tuple: (search_results, source_type)
    """
    try:
        # Sử dụng router để quyết định hướng tìm kiếm
        search_strategy = route_search(question)
        
        search_type = search_strategy.get("type_search")
        keywords = search_strategy.get("key_word", [])
        
        if search_type == "vector_db":
            results = search_from_vector_db(keywords)
            return results, "vector_db"
            
        elif search_type == "web_search":
            results = web_search_keywords(keywords, max_results, domain_restrict)
            return results, "web_search"
            
        else:
            results = web_search_keywords([question], max_results, domain_restrict)
            return results, "web_search"
            
    except Exception as e:
        # Fallback to web search
        results = web_search_keywords([question], max_results, domain_restrict)
        return results, "web_search"

# Backward compatibility - keep old function name but use new logic
def web_search(question, max_results, domain_restrict=False):
    """Backward compatibility wrapper"""
    results, source_type = unified_search(question, max_results, domain_restrict)
    return results
    
def extract_tables(soup):
    tables = soup.find_all("table")
    results = []
    for table in tables:
        try:
            df = pd.read_html(StringIO(str(table)))[0]
            if df.shape[0] > 1:
                results.append(df)
        except:
            continue
    return results

def extract_main_content(url):
    try:
        main_content = ""

        response = requests.get(url, verify=False, timeout=10)
        html = response.text
        article = Article(url, language='vi')
        article.set_html(html)
        article.parse()
        
        main_content += article.text.strip()
        
        soup = BeautifulSoup(response.content, "html.parser")
        tables = extract_tables(soup)
        if tables:
            main_content += "\n\n" + "\n\n".join([table.to_string(index=False) for table in tables])
        if main_content:
            return main_content
        else:
            return "Không tìm được nội dung có thể xử lý."    
    except Exception:
        return None

def get_source(query, max_results, domain_restrict=False):
    """
    Lấy nguồn thông tin - tự động chọn từ vector DB hoặc web search
    
    Returns:
        List[dict] với format:
        - url: URL nguồn
        - title: Tiêu đề
        - description: Mô tả  
        - text: Nội dung đầy đủ
        - source: "vector_db" hoặc "web_search"
    """
    try:
        search_source = []
        results, source_type = unified_search(query, max_results, domain_restrict)
        
        if results is None:
            return None
            
        for result in results:
            if source_type == "vector_db":
                # Vector DB results đã có đầy đủ thông tin
                search_source.append({
                    "url": result["url"],
                    "title": result["title"], 
                    "description": result["description"],
                    "text": result["text"],
                    "source": "vector_db"
                })
            else:
                # Web search results cần extract content
                url = result["url"]
                try:
                    content = extract_main_content(url)
                    search_source.append({
                        "url": url,
                        "title": result["title"],
                        "description": result["description"],
                        "text": content,
                        "source": "web_search"
                    })
                except Exception as e:
                    # Vẫn thêm với description làm content
                    search_source.append({
                        "url": url,
                        "title": result["title"],
                        "description": result["description"],
                        "text": result["description"],
                        "source": "web_search"
                    })
                
        return search_source
        
    except Exception as e:
        return None
