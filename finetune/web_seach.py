from bs4 import BeautifulSoup
from newspaper import Article
from io import StringIO
import pandas as pd
import requests

def generate_search_keywords(question, client):
    """Hỏi GPT một câu hỏi và trả về kết quả"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """Bạn là chuyên gia tạo từ khóa tìm kiếm điểm chuẩn các trường đại học. Nhiệm vụ: phân tích câu hỏi và tạo từ khóa giúp tìm được thông tin LLM có thể suy luận ra câu trả lời.

CHIẾN LƯỢC TÌM KIẾM:

1. **Phân tích câu hỏi**: Xác định tên trường và năm, nếu không có năm thì để trống.
2. **Tạo từ khóa tìm kiếm**: Có dạng: Điểm chuẩn + tên trường + (năm)

VÍ DỤ:

Câu hỏi: "Ngành Trí tuệ nhân tạo UET 2024 lấy bao nhiêu điểm"
Trả về : "Điểm chuẩn UET 2024" hoặc "Điểm chuẩn trường Đại học Công nghệ - Đại học Quốc gia Hà Nội 2024"

Chỉ trả về từ khóa, không giải thích."""
            },
            {   "role": "user",
                "content": question
            }
        ],
    )
    return response.choices[0].message.content.strip().replace('"', '').replace("'", "")

def web_search(question, client, BRAVE_API_KEY, max_results=3):
    """Tìm kiếm thông tin từ web sử dụng Brave Search API"""
    try:
        query = generate_search_keywords(question, client)
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
        urls = []
        for result in results[:max_results]:
            url = result.get("url", "")
            urls.append(url)
        return urls
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
        
        soup = BeautifulSoup(response.content, "html.parser")
        tables = extract_tables(soup)
        if tables:
            main_content += "\n\n" + "\n\n".join([table.to_string(index=False) for table in tables])
        if main_content:
            return main_content
        else:
            return ""    
    except Exception as e:
        return ""
    
def get_context_from_web(question, client, BRAVE_API_KEY):
    urls = web_search(question, client, BRAVE_API_KEY)
    context = ""
    for url in urls:
        context += extract_main_content(url) + "\n" + 100*"-" + "\n"
    return context
