import requests
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup, Tag
import requests
from urllib.parse import urljoin
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"D:\Tesseract-OCR\tesseract.exe"
from io import BytesIO, StringIO
from PIL import Image

def get_api_key():
    load_dotenv('api_key.env')
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
    return {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "BRAVE_API_KEY": BRAVE_API_KEY
    }

def build_web_search(query, max_results=3):
    """Tìm kiếm thông tin từ web sử dụng Brave Search API"""
    BRAVE_API_KEY = get_api_key()["BRAVE_API_KEY"]
    
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
    
def extract_main_content(url):
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.content, "html.parser")

        for tag in soup(["header", "footer", "nav", "aside", "script", "style", "form", "noscript"]):
            tag.decompose()
        content_parts = []

        # Lấy tất cả các thẻ có thể chứa nội dung theo thứ tự
        for element in soup.body.descendants:
            if isinstance(element, Tag):
                if element.name in ["p", "h1", "h2", "h3", "h4", "h5", "h6", "div"]:
                    text = element.get_text(strip=True)
                    if text:
                        content_parts.append(text)

                elif element.name == "table":
                    try:
                        import pandas as pd
                        table = pd.read_html(StringIO(str(table)))[0]
                        content_parts.append(table.to_string())
                    except Exception:
                        continue  # Bỏ qua nếu không đọc được bảng

                elif element.name == "img":
                    # Lấy nội dung OCR từ ảnh (nếu có src hợp lệ)
                    img_url = element.get("src")
                    if img_url:
                        try:
                            ocr_text = extract_text_from_image_url(img_url, base_url=url)
                            if ocr_text:
                                content_parts.append(ocr_text.strip())
                        except Exception:
                            continue

        if content_parts:
            return "\n\n".join(content_parts)
        else:
            return "Không tìm được nội dung có thể xử lý."

    except Exception as e:
        return f"Lỗi khi xử lý URL: {e}"
    
def build_web_search_context(query, max_results=3):
    pages = build_web_search(query, max_results)
    context = ""
    for page in pages.values():
        url = page["url"]
        context += f"Nguồn {url}" + "\n\n"
        context += extract_main_content(url) + 100*'-' + "\n\n"
    # with open("web_search_context.txt", "w", encoding="utf-8") as f:
    #     f.write(context)
    return context