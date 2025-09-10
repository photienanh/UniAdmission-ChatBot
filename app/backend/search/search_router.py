import ast
from openai import OpenAI
import os
from typing import Dict, List, Union
from .localdb_search import search_from_local_database
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

1. **Xác định nguồn tìm kiếm**: Có 2 nguồn để tìm kiếm là tìm trên local database hoặc tìm trên web.
    - Local DB: Chứa thông tin về các trường đại học: thông tin chung của trường(tên trường, địa chỉ, website, thông tin liên hệ), điểm chuẩn các năm gần đây, học phí, các ngành đào tạo và thông tin tuyển sinh.
    - Web search: Tìm trên web nếu chủ đề câu hỏi không có trong local DB, ví dụ như: danh sách giảng viên, học bổng, bảng xếp hạng,...
2. **Xác định tên viết tắt của trường**: Nếu câu hỏi có liên quan đến trường đại học cụ thể, hãy xác định tên viết tắt chính xác của trường đó, khi tìm trên local DB luôn luôn sử dụng tên viết tắt, web search thì ưu tiên dùng tên viết tắt nếu có thể.
    Một số tên viết tắt phổ biến:
    - Trường Đại học Công nghệ - ĐHQG Hà Nội: UET
    - Trường Đại học Khoa học Tự nhiên - ĐHQG Hà Nội: HUS
    - Đại học Bách khoa Hà Nội: HUST
    - Đại học Kinh tế Quốc dân: NEU
    - Đại học Ngoại thương: FTU
    - Đại học Thương mại: TMU
    - Đại học Luật Hà Nội: HLU
    - Đại học sư phạm Hà Nội: HNUE
    - Đại học Y Hà Nội: HMU
    - Đại học Công nghiệp Hà Nội: HAUI
    - Trường Đại học Luật - ĐHQG Hà Nội: LS(đối với local DB), VNU-UL(đối với web search)
    - Trường Đại học Kinh tế - ĐHQG Hà Nội: UEB
    - Trường Đại học Ngoại ngữ - ĐHQG Hà Nội: ULIS
    - Trường Đại học Khoa học Xã hội và Nhân văn - ĐHQG Hà Nội: USSH
    - Đại học Giao thông Vận tải: UTC
    - Học viện Công nghệ Bưu chính Viễn thông: PTIT
    - Học viện Kĩ thuật mật mã: ACT(đối với local DB), KMA(đối với web search)
    - Học viện Báo chí và Tuyên truyền: AJC
    ...
    Nếu câu hỏi chung chung không liên quan đến trường cụ thể nào, thì không cần lấy tên viết tắt, đồng thời luôn sử dụng web search.
3. **Xác định từ khóa tìm kiếm**:
    - Đối với tìm trên local DB: dùng 1 trong 4 từ khóa sau: "thong_tin_chung" (đối với các câu hỏi liên quan đến thông tin chung của trường như địa chỉ, thông tin liên hệ,...), "diem_chuan" (đối với các câu hỏi liên quan đến điểm chuẩn), "hoc_phi" (đối với các câu hỏi liên quan đến học phí của trường) và "tuyen_sinh" (đối với các câu hỏi liên quan đến thông tin tuyển sinh, các ngành đào tạo của trường).
    - Đối với tìm trên web: tóm tắt câu hỏi thành từ khóa chính làm sao để khi tìm kiếm các trang hiện ra sẽ có chứa thông tin cần thiết để trả lời câu hỏi. Ví dụ như hỏi số Tiến sĩ của trường thì không thể tìm trực tiếp ra số tiến sĩ được, mà phải tìm "danh sách giảng viên của trường", từ thông tin danh sách giảng viên LLM sẽ đếm số tiến sĩ.
    Một số ví dụ cho từ khóa tìm trên web:
    "danh sách giảng viên viện trí tuệ nhân tạo trường đại học công nghệ đhqg hà nội" → "danh sách giảng viên viện trí tuệ nhân tạo UET"
    "học phần chương trình đào tạo ngành trí tuệ nhân tạo UET" → "chương trình đào tạo ngành trí tuệ nhân tạo UET"
    "số tiến sĩ của khoa công nghệ thông tin ptit" → "danh sách giảng viên khoa công nghệ thông tin ptit"
    "danh sách giảng viên của đại học kinh tế quốc dân. có bao nhiêu người là PGS" → "danh sách giảng viên NEU"
    "chương trình đào tạo ngành khoa học máy tính của đại học bách khoa hà nội. tổng cộng có bao nhiêu học phần. học phần nào nhiều tín chỉ nhất" → "chương trình đào tạo ngành khoa học máy tính HUST"
    "tỉ lệ sinh viên có việc làm sau khi tốt nghiệp của đại học ngoại thương" → "tỉ lệ việc làm FTU"
    "danh sách giảng viên ngôn ngữ anh trường đại học ngoại ngữ. không tính trợ giảng" → "danh sách giảng viên ngôn ngữ anh ULIS"
    ""
4. **Định dạng kết quả**:
    Kết quả trả về có địng dạng như sau, tùy thuộc vào nguồn tìm kiếm:
    {"type_search": "local_db", "key_word": [{"school_id":"tên viết tắt của trường 1", "section":"section 1"}, {"school_id":"tên viết tắt của trường 2", "section":"section 2"}, ...]}
    hoặc {"type_search": "web_search", "key_word": ["từ khóa tìm kiếm 1", "từ khóa tìm kiếm 2", ...]}
    Ví dụ: {"type_search": "local_db", "key_word": [{"school_id":"UET", "section":"diem_chuan"}]}, {"type_search": "web_search", "key_word": ["danh sách giảng viên của UET"]}
5. **Ví dụ cụ thể**:
    "UET có các khoa/viện nào" → {"type_search": "web_search", "key_word": ["cơ câu tổ chức UET"]}
    "điểm chuẩn năm 2025 của UET. ngành CNTT tăng hay giảm so với năm 2024" → {"type_search": "local_db", "key_word": [{"school_id":"UET", "section":"diem_chuan"}]}
    "học phí năm 2025 của đại học kinh tế quốc dân" → {"type_search": "local_db", "key_word": [{"school_id":"NEU", "section":"hoc_phi"}]}
    "địa chỉ và thông tin liên hệ của đại học sư phạm hà nội" → {"type_search": "local_db", "key_word": [{"school_id":"HNUE", "section":"thong_tin_chung"}]}
    "so sánh điểm chuẩn ngành CNTT của UET và HUST năm 2024" → {"type_search": "local_db", "key_word": [{"school_id":"UET", "section":"diem_chuan"}, {"school_id":"HUST", "section":"diem_chuan"}]}
    "viện trí tuệ nhân tạo UET có bao nhiêu tiến sĩ" → {"type_search": "web_search", "key_word": ["danh sách giảng viên viện trí tuệ nhân tạo UET"]}
    "tổng số tín chỉ chương trình đào tạo ngành y đa khoa của đại học y hà nội" → {"type_search": "web_search", "key_word": ["chương trình đào tạo ngành y đa khoa HMU"]}
    "năm 2025 đại học ngoại thương tuyển sinh bao nhiêu ngành đào tạo" → {"type_search": "local_db", "key_word": [{"school_id":"FTU", "section":"tuyen_sinh"}]}
    "bảng xếp hạng các trường đại học ở việt nam năm 2025" → {"type_search": "web_search", "key_word": ["bảng xếp hạng các trường đại học ở việt nam năm 2025"]}
    "Học viện công nghệ bưu chính viễn thông có bao nhiêu sinh viên, so với UET thì sao" → {"type_search": "web_search", "key_word": ["số lượng sinh viên PTIT", "số lượng sinh viên UET"]}
    ...
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

def search(question: str, max_results: int, domain_restrict: bool = False) -> Union[List[dict], None]:
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
        
        if type_search == "local_db":
            results = search_from_local_database(keywords)
            if results:
                for result in results:
                    if any("tuyen_sinh" in kw.get("section", "") for kw in keywords) and len(result["text"].split()) <= 50:
                        return search_from_web([question], max_results, domain_restrict)
                    elif any("hoc_phi" in kw.get("section", "") for kw in keywords) and len(result["text"].split()) <= 20:
                        return search_from_web([question], max_results, domain_restrict)
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