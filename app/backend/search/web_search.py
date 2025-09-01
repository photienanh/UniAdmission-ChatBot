import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
from newspaper import Article
from io import StringIO
import os
from typing import List
import urllib3
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
            
            searched_pages = data.get("web", {}).get("results", [])

            for page in searched_pages[:max_results]:
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