import requests
import pandas as pd
import ast
import time
from openai import OpenAI
from bs4 import BeautifulSoup
from newspaper import Article
from io import StringIO
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Get API keys from environment
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
GPT_API_KEY = os.getenv("GPT_API_KEY")

def initialize_openai_client():
    return OpenAI(
        api_key=GPT_API_KEY
    )

def generate_search_keywords(question, model="gpt-4o-mini"):
    
    # Check API key
    if not GPT_API_KEY:
        return question
        
    try:
        client = initialize_openai_client()
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": """Bạn là chuyên gia tạo từ khóa tìm kiếm thông minh. Nhiệm vụ: phân tích câu hỏi và tạo từ khóa giúp tìm được thông tin CĂN BẢN để LLM có thể suy luận ra câu trả lời.

CHIẾN LƯỢC TÌM KIẾM:

1. **Phân tích ý định câu hỏi**: Xác định thông tin gì cần thiết để trả lời
2. **Tìm nguồn thông tin gốc**: Thay vì tìm trực tiếp câu trả lời, tìm dữ liệu để suy luận
3. **Tối ưu từ khóa**: Dùng thuật ngữ chính thức, tên đầy đủ
4. **Trả lời đúng định dạng**: Định dạng câu trả lời như sau: ["từ khóa tìm kiếm 1", "từ khóa tìm kiếm 2", ...]

VÍ DỤ THÔNG MINH:

Câu hỏi: "Số tiến sĩ trong viện trí tuệ nhân tạo UET là bao nhiêu?"
→ Cần: Danh sách giảng viên để đếm tiến sĩ
→ Từ khóa: "danh sách giảng viên viện trí tuệ nhân tạo UET"
→ Trả về: ["danh sách giảng viên viện trí tuệ nhân tạo UET"]

Câu hỏi: "Điểm chuẩn ngành CNTT Bách Khoa 2024?"  
→ Cần: Bảng điểm chuẩn chính thức
→ Từ khóa: "điểm chuẩn đại học Bách Khoa Hà Nội 2024"
→ Trả về: ["điểm chuẩn đại học Bách Khoa Hà Nội 2024"]

Câu hỏi: "Học phí ngành AI VNU-UET như thế nào?"
→ Cần: Bảng học phí chính thức  
→ Từ khóa: "học phí đại học công nghệ VNU-UET 2024"
→ Trả về: ["học phí đại học công nghệ VNU-UET 2024"]

Câu hỏi: "Chương trình đào tạo ngành CNTT có môn gì?"
→ Cần: Khung chương trình chi tiết
→ Từ khóa: "chương trình đào tạo ngành công nghệ thông tin UET"
→ Trả về: ["chương trình đào tạo ngành công nghệ thông tin UET"]

Câu hỏi: "So sánh điểm chuẩn CNTT Bách Khoa và UET?"
→ Cần: Bảng điểm chuẩn chính thức của cả hai trường
→ Từ khóa: "điểm chuẩn đại học Bách Khoa Hà Nội 2024", "điểm chuẩn đại học công nghệ VNU-UET 2024"
→ Trả về: ["điểm chuẩn đại học Bách Khoa Hà Nội 2024", "điểm chuẩn đại học công nghệ VNU-UET 2024"]

NGUYÊN TẮC:
- Thêm năm học nếu cần thông tin mới nhất
- Tìm "danh sách", "bảng", "chương trình" thay vì câu hỏi trực tiếp

Chỉ trả về từ khóa, không giải thích."""
                },
                {   "role": "user",
                    "content": question
                }
            ],
        )
        keywords = response.choices[0].message.content.strip()
        keywords = ast.literal_eval(keywords)
        return keywords
    except Exception:
        return [question]

def web_search(question, max_results, domain_restrict=False):
    """Tìm kiếm thông tin từ web sử dụng Brave Search API"""
    
    # Check API key
    if not BRAVE_API_KEY:
        return None
        
    try:
        query = generate_search_keywords(question)
        pages = []
        for q in query:
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
                return None
                
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
    try:
        search_source = []
        pages = web_search(query, max_results, domain_restrict)
        
        if pages is None:
            return None
            
        for page in pages:
            url = page["url"]
            try:
                content = extract_main_content(url)
                search_source.append({
                    "url": url,
                    "title": page["title"],
                    "description": page["description"],
                    "text": content
                })
            except Exception as e:
                pass
                
        return search_source
    except Exception:
        return None
