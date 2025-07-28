import requests
import os
import pandas as pd
from bs4 import BeautifulSoup, Tag
from newspaper import Article
from io import BytesIO, StringIO
from PIL import Image
from dotenv import load_dotenv
from urllib.parse import urljoin
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"D:\Tesseract-OCR\tesseract.exe"

def get_api_key():
    load_dotenv('api_key.env')
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
    return {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "BRAVE_API_KEY": BRAVE_API_KEY
    }

def web_search(query, max_results=3):
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
        return
    
def extract_text_from_image_url(img_url, base_url=None):
    try:
        # Xử lý URL tương đối thành tuyệt đối nếu cần
        if base_url:
            img_url = urljoin(base_url, img_url)

        # Tải ảnh từ URL
        response = requests.get(img_url, timeout=10)
        response.raise_for_status()  # Gây lỗi nếu ảnh không tải được

        # Mở ảnh bằng PIL
        image = Image.open(BytesIO(response.content)).convert("RGB")

        # Dùng pytesseract để OCR
        text = pytesseract.image_to_string(image, lang="eng+vie")  # có thể thêm "vie" nếu có tiếng Việt

        return text.strip()

    except Exception as e:
        return ""
    
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
            return "\n\n".join(main_content)
        else:
            return "Không tìm được nội dung có thể xử lý."    

    except Exception as e:
        return f"Lỗi khi xử lý URL: {e}"
    
def build_web_search_context(query, max_results=3):
    try:
        pages = web_search(query, max_results)
        if pages is None:
            return ""
        context = ""
        for page in pages.values():
            url = page["url"]
            context += f"Nguồn {url}" + "\n\n"
            context += extract_main_content(url) + 100*'-' + "\n\n"
            
        return context
    except:
        return ""