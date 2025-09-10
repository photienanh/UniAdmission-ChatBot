import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
from newspaper import Article
from io import StringIO
import json
import os
import re
import numpy as np
from typing import List
import urllib3
from ..cache.database_cache import get_global_embedding_model
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Get API keys from environment
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")

def search_from_web(keywords, max_results, domain_restrict=False) -> List[dict]:
    """Tìm kiếm thông tin từ web với danh sách keywords"""
    
    # Check API key
    if not BRAVE_API_KEY:
        return None
        
    try:
        results = []
        for q in keywords:
            # Brave Search API endpoint
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": BRAVE_API_KEY}
            params = {
                "q": q,
                "count": max_results * 4,
                "search_lang": "vi",  # Vietnamese language
                "safesearch": "moderate",
                "text_decorations": "false",  # Không cần đánh dấu văn bản
            }
            
            response = requests.get(url, headers=headers, params=params)
            time.sleep(1)
        
            if response.status_code != 200:
                continue
                
            data = response.json()
            
            searched_pages = data.get("web", {}).get("results", [])
            final_pages = rerank_search_results(searched_pages, q, max_results)

            for page in final_pages[:max_results]:
                title = page.get("title", "")
                description = page.get("description", "")
                url = page.get("url", "")
                content = title + "\n\n" + extract_main_content(url) if extract_main_content(url) else "Không thể trích xuất nội dung"
                
                if title and description:
                    item = {
                        "url": url,
                        "title": title,
                        "description": description,
                        "text": content,
                        "source": "web_search"
                    }
                    results.append(item)
                
        return results
    except Exception:
        return None

def extract_tables(soup: BeautifulSoup) -> List[pd.DataFrame]:
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

def extract_main_content(url: str) -> str:
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

        return main_content
    except Exception:
        return ""
    
def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-zA-Z0-9\u00C0-\u1EF9\s\.,;]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def detect_school(query: str, schools: dict) -> str | None:
        """Detect school from query using predefined keywords"""
        for school, aliases in schools.items():
            if any(alias in query for alias in aliases):
                return school
        return None

def rerank_search_results(results: List[dict], query: str, top_k: int) -> List[dict]:
    """Rerank search results using embedding similarity"""
    schools = {
        school: [normalize_text(alias) for alias in aliases]
        for school, aliases in json.load(open("./backend/search/schools.json", "r", encoding="utf-8")).items()
    }
    embedding = get_global_embedding_model()
    
    # If no embedding model available, return original results
    if not embedding:
        return results[:top_k]
    
    query_norm = normalize_text(query)
    detected_school = detect_school(query_norm, schools)
    
    try:
        query_emb = embedding.embed_query(query_norm)
        
        scored_results = []
        for result in results:
            title = result.get("title", "") or ""
            desc = result.get("description", "") or ""
            url = result.get("url", "") or ""

            # Chuẩn hóa
            title_norm = normalize_text(title)
            desc_norm = normalize_text(desc)
            url_norm = normalize_text(url)

            # Semantic embedding
            title_emb = embedding.embed_query(title_norm) if title_norm else None
            desc_emb = embedding.embed_query(desc_norm) if desc_norm else None
            url_emb = embedding.embed_query(url_norm) if url_norm else None

            # Cosine similarity
            def cos_sim(a, b):
                norm_a = np.linalg.norm(a)
                norm_b = np.linalg.norm(b)
                if norm_a == 0 or norm_b == 0:
                    return 0.0
                return float(np.dot(a, b) / (norm_a * norm_b))

            score = 0.0
            weights = {"title": 0.5, "desc": 0.3, "url": 0.2}
            if title_emb is not None:
                score += cos_sim(query_emb, title_emb) * weights["title"]
            if desc_emb is not None:
                score += cos_sim(query_emb, desc_emb) * weights["desc"]
            if url_emb is not None:
                score += cos_sim(query_emb, url_emb) * weights["url"]

            # Heuristic ưu tiên trường trong query
            if detected_school:
                aliases = [normalize_text(a) for a in schools.get(detected_school, [])]
                if any(a in text for a in aliases for text in [url_norm, title_norm, desc_norm]):
                    score += 0.5
                else:
                    for school, other_aliases in schools.items():
                        if school != detected_school:
                            other_aliases_norm = [normalize_text(a) for a in other_aliases]
                            if any(a in text for a in other_aliases_norm for text in [url_norm, title_norm, desc_norm]):
                                score -= 0.5

            # Heuristic boost
            if any(kw in query_norm for kw in ["tuyển sinh", "ngành đào tạo"]):
                if "tuyensinh247" in url_norm:
                    score += 0.1
                if url_norm.endswith(".edu") or ".edu.vn" in url_norm:
                    score += 0.2

            scored_results.append((result, score))

        # Sort theo score giảm dần
        scored_results.sort(key=lambda x: x[1], reverse=True)
        final_results = [res for res, _ in scored_results[:top_k]]

        return final_results
        
    except Exception:
        # If any error occurs, return original results
        return results[:top_k]

