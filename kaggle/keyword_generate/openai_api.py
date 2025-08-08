# From web_search.py

from openai import OpenAI
from .config import GPT_API_KEY
def initialize_openai_client():
    return OpenAI(
        base_url="https://models.github.ai/inference",
        api_key=GPT_API_KEY
    )

def generate_search_keywords(question, model="openai/gpt-4o-mini"):
    """Hỏi GPT một câu hỏi và trả về kết quả"""
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

VÍ DỤ THÔNG MINH:

Câu hỏi: "Số tiến sĩ trong viện trí tuệ nhân tạo UET là bao nhiêu?"
→ Cần: Danh sách giảng viên để đếm tiến sĩ
→ Từ khóa: "danh sách giảng viên viện trí tuệ nhân tạo UET"

Câu hỏi: "Điểm chuẩn ngành CNTT Bách Khoa 2024?"  
→ Cần: Bảng điểm chuẩn chính thức
→ Từ khóa: "điểm chuẩn đại học Bách Khoa Hà Nội 2024"

Câu hỏi: "Học phí ngành AI VNU-UET như thế nào?"
→ Cần: Bảng học phí chính thức  
→ Từ khóa: "học phí đại học công nghệ VNU-UET 2024"

Câu hỏi: "Chương trình đào tạo ngành CNTT có môn gì?"
→ Cần: Khung chương trình chi tiết
→ Từ khóa: "chương trình đào tạo ngành công nghệ thông tin UET"

Câu hỏi: "Đại học Bách khoa"
→ Cần: Thông tin Đại học Bách khoa
→ Từ khóa: "đại học Bách khoa"

Câu hỏi: "Tuyển sinh Đại học Bách khoa"
→ Cần: Thông tin tuyển sinh Đại học Bách khoa
→ Từ khóa: "tuyển sinh đại học Bách khoa"

NGUYÊN TẮC:
- Thêm năm học nếu cần thông tin mới nhất
- Tìm "danh sách", "bảng", "chương trình" thay vì câu hỏi trực tiếp
- Ưu tiên trang web chính thức (.edu.vn)

Chỉ trả về từ khóa, không giải thích."""
            },
            {   "role": "user",
                "content": question
            }
        ],
    )
    return response.choices[0].message.content.strip()
