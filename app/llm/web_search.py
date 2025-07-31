import requests
import os
import pandas as pd
from bs4 import BeautifulSoup
from newspaper import Article
from io import StringIO
from config import BRAVE_API_KEY
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def web_search(query, max_results):
    """Tìm kiếm thông tin từ web sử dụng Brave Search API"""
    try:
        # Brave Search API endpoint
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": BRAVE_API_KEY}
        params = {
            "q": query,
            "count": max_results,
            "search_lang": "vi",  # Vietnamese language
            "safesearch": "moderate",
            "text_decorations": "false",  # Không cần đánh dấu văn bản
        }
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        results = data.get("web", {}).get("results", [])
        
        pages = {}
        for i, result in enumerate(results[:max_results], 1):
            title = result.get("title", "")
            description = result.get("description", "")
            url = result.get("url", "")
            
            if title and description:
                item = {
                    "title": title,
                    "description": description,
                    "url": url
                }
            pages[f"Nguồn {i}"] = item
        return pages
    except:
        return None
    
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

        response = requests.get(url, verify=False)
        html = response.text
        article = Article(url, language='vi')
        article.set_html(html)
        article.parse()
        
        main_content += article.text.strip()

        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        tables = extract_tables(soup)
        if tables:
            main_content += "\n\n" + "\n\n".join([table.to_string(index=False) for table in tables])
        if main_content:
            return main_content
        else:
            return "Không tìm được nội dung có thể xử lý."    
    except Exception as e:
        return f"Lỗi khi xử lý URL: {e}"
def get_source(query, max_results):
    try:
        search_source = []
        context = ""
        pages = web_search(query, max_results)
        if pages is None:
            return None, None
        for page in pages.values():
            url = page["url"]
            content = extract_main_content(url)
            search_source.append({
                "url": url,
                "title": page["title"],
                "description": page["description"],
                "content": content
            })
            context += content + 100*'-' + "\n\n"
        return context, search_source
    except:
        return None, None
