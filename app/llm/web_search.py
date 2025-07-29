import requests
import os
import pandas as pd
from bs4 import BeautifulSoup
from newspaper import Article
from io import StringIO
from dotenv import load_dotenv

def get_api_key():
    load_dotenv('api_key.env')
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
    return {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "BRAVE_API_KEY": BRAVE_API_KEY
    }

def web_search(query, max_results):
    """Tìm kiếm thông tin từ web sử dụng Brave Search API"""
    try:
        BRAVE_API_KEY = get_api_key()["BRAVE_API_KEY"]
        if not BRAVE_API_KEY:
            return
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
            snippet = result.get("description", "")
            url = result.get("url", "")
            
            if title and snippet:
                item = {
                    "title": title,
                    "snippet": snippet,
                    "url": url
                }
            pages[f"Nguồn {i}"] = item
        
        return pages
    except:
        return None
    
# def extract_text_from_image_url(img_url, base_url=None):
#     try:
#         # Xử lý URL tương đối thành tuyệt đối nếu cần
#         if base_url:
#             img_url = urljoin(base_url, img_url)

#         # Tải ảnh từ URL
#         response = requests.get(img_url, timeout=10)
#         response.raise_for_status()  # Gây lỗi nếu ảnh không tải được

#         # Mở ảnh bằng PIL
#         image = Image.open(BytesIO(response.content)).convert("RGB")

#         # Dùng pytesseract để OCR
#         text = pytesseract.image_to_string(image, lang="eng+vie")

#         return text.strip()

#     except Exception as e:
#         return ""
    
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

        article = Article(url, language='vi')
        article.download()
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
        source = {}
        pages = web_search(query, max_results)
        if pages is None:
            return None
        for i, page in enumerate(pages.values(), 1):
            url = page["url"]
            source[i] = {
                "url": url,
                "title": page["title"],
                "content": extract_main_content(url)
            }
            
        return source
    except:
        return None
