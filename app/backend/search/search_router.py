import ast
from openai import OpenAI
import os
from typing import Dict, List, Union
from .vectordb_search import search_from_vector_db
from .web_search import search_from_web

# Get API key from environment
GPT_API_KEY = os.getenv("GPT_API_KEY")

def initialize_openai_client() -> OpenAI:
    """Initialize OpenAI client"""
    return OpenAI(api_key=GPT_API_KEY)

def generate_search_keywords(question: str, model: str = "gpt-4o-mini") -> Dict[str, Union[str, List]]:
    # Check API key
    if not GPT_API_KEY:
        return {"type_search": "web_search", "key_word": [question]}
        
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
2. **Xác định nguồn tìm kiếm**: Tìm kiếm từ local vector database hoặc tìm kiếm trên web. Vector DB có chứa thông tin về điểm chuẩn các năm, thông tin chung của trường, học phí và thông tin tuyển sinh. Các câu hỏi ngoài phạm vi của Vector DB sẽ tìm kiếm trên web.
2. **Tìm nguồn thông tin gốc**: Thay vì tìm trực tiếp câu trả lời, tìm dữ liệu để suy luận
3. **Tối ưu từ khóa**: Dùng thuật ngữ chính thức, tên đầy đủ
4. **Trả lời đúng định dạng**: Định dạng câu trả lời như sau:
- Nếu sử dụng web search: {"type_search": "web_search", "key_word": ["từ khóa 1", "từ khóa 2", ...]}
- Nếu sử dụng local vector DB: {"type_search": "vector_db", "key_word": [{"school_id": "tên trường 1", "section": "section1"},{"school_id": "tên trường 2", "section": "section2"},...]}. Lưu ý: section là 1 trong 4 mục: "thong_tin_chung", "hoc_phi", "diem_chuan", "tuyen_sinh", trong đó "thong_tin_chung" bao gồm thông tin chung của trường như tên, địa chỉ, liên hệ..., "hoc_phi" bao gồm thông tin học phí của trường, "diem_chuan" bao gồm điểm chuẩn các năm, "tuyen_sinh" bao gồm các ngành đào tạo của trường, thông tin tuyển sinh của truờng.

VÍ DỤ THÔNG MINH:

Câu hỏi: "Số tiến sĩ trong viện trí tuệ nhân tạo UET là bao nhiêu?"
→ Không có trong vector DB nên cần tìm kiếm trên web
→ Cần: Danh sách giảng viên để đếm tiến sĩ
→ Từ khóa: "danh sách giảng viên viện trí tuệ nhân tạo UET"
→ Trả về: {"type_search": "web_search", "key_word": ["danh sách giảng viên viện trí tuệ nhân tạo UET"]}

Câu hỏi: "Điểm chuẩn UET 2024?"
→ Vector DB có thông tin điểm chuẩn các năm nên tìm trong DB
→ Cần: Điểm chuẩn của Đại học Công nghệ - Đại học Quốc gia Hà Nội (UET)
→ Trả về: {"type_search": "vector_db", "key_word": [{"school_id": "UET", "section": "diem_chuan"}]}

Câu hỏi: "Điểm chuẩn ngành CNTT Bách Khoa 2025?"
→ Vector DB có thông tin điểm chuẩn các năm nên tìm trong DB
→ Cần: Điểm chuẩn của Đại học Bách Khoa (HUST)
→ Trả về: {"type_search": "vector_db", "key_word": [{"school_id": "HUST", "section": "diem_chuan"}]}

Câu hỏi: "Học phí ngành Luật kinh doanh VNU-LS như thế nào?"
→ Vector DB có thông tin học phí nên tìm trong DB
→ Cần: Học phí của Trường Đại học Luật - Đại học Quốc gia Hà Nội (LS)
→ Trả về: {"type_search": "vector_db", "key_word": [{"school_id": "LS", "section": "hoc_phi"}]}

Câu hỏi: "Toàn bộ học phần chương trình đào tạo ngành Ngôn ngữ Anh Trường Đại học Ngoại ngữ - Đại học Quốc gia Hà Nội?"
→ Vector DB không có thông tin cụ thể về chương trình đào tạo của từng ngành nên cần tìm kiếm trên web
→ Cần: Học phần chương trình đào tạo ngành Ngôn ngữ Anh của Trường Đại học Ngoại ngữ - Đại học Quốc gia Hà Nội (ULIS)
→ Trả về: {"type_search": "web_search", "key_word": ["học phần chương trình đào tạo ngành Ngôn ngữ Anh ULIS"]}

Câu hỏi: "Địa chỉ của UEB và Học viện Công nghệ Bưu chính Viễn thông?"
→ Vector DB có thông tin chung như địa chỉ nên tìm trong DB
→ Trả về: {"type_search": "vector_db", "key_word": [{"school_id": "UEB", "section": "thong_tin_chung"},{"school_id": "PTIT", "section": "thong_tin_chung"}]}

NGUYÊN TẮC:
- Các câu hỏi ngoài phạm vi vector DB (thông tin chung (gồm tên trường, giới thiệu, mã trường, địa chỉ, thông tin liên hệ như điện thoại, web ...), điểm chuẩn các năm, học phí, thông tin tuyển sinh) thì tìm kiếm trên web
- Nếu câu hỏi cần tìm thông tin mới nhất, ví dụ trong câu hỏi có từ khóa như "mới nhất", "cập nhật",... thì ưu tiên tìm kiếm trên web
- Tìm "danh sách", "bảng", "chương trình" thay vì câu hỏi trực tiếp

Chỉ trả về từ khóa, không giải thích."""
                },
                {
                    "role": "user",
                    "content": question
                }
            ],
        )
        
        keywords_text = response.choices[0].message.content.strip()
        keywords = ast.literal_eval(keywords_text)
        
        return keywords
        
    except Exception as e:
        # Fallback to web search
        return {"type_search": "web_search", "key_word": [question]}

def route_search(question: str) -> Dict[str, Union[str, List]]:
    try:
        search_strategy = generate_search_keywords(question)
        
        # Validate format
        if not isinstance(search_strategy, dict):
            raise ValueError("Invalid search strategy format")
            
        if "type_search" not in search_strategy or "key_word" not in search_strategy:
            raise ValueError("Missing required fields in search strategy")
            
        return search_strategy
        
    except Exception as e:
        # Fallback
        return {"type_search": "web_search", "key_word": [question]}

def search(question: str, max_results: int, domain_restrict: bool =False) -> Union[List[dict], None]:
    """
    Tìm kiếm thống nhất sử dụng router để quyết định nguồn
    
    Returns:
        tuple: (search_results, source_type)
    """
    try:
        # Sử dụng router để quyết định hướng tìm kiếm
        search_strategy = route_search(question)
        
        type_search = search_strategy.get("type_search")
        keywords = search_strategy.get("key_word", [])
        
        if type_search == "vector_db":
            results = search_from_vector_db(keywords)
            if results:
                return results
            else:
                # Fallback to web search with original question
                results = search_from_web([question], max_results, domain_restrict)
                return results
            
        elif type_search == "web_search":
            results = search_from_web(keywords, max_results, domain_restrict)
            return results
            
        else:
            # Fallback to web search with original question
            results = search_from_web([question], max_results, domain_restrict)
            return results
            
    except Exception as e:
        # Fallback to web search with original question
        results = search_from_web([question], max_results, domain_restrict)
        return results