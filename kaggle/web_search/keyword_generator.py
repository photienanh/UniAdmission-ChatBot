import ast
from typing import List, Optional
import os

class KeywordGenerator:
    """
    Simple keyword generator using GPT-4o-mini to rewrite query into search keywords
    """
    
    def __init__(self, gpt_api_key: Optional[str] = None):
        """
        Initialize with GPT-4o-mini
        
        Args:
            gpt_api_key: OpenAI API key. If None, will try to get from environment
        """
        self.openai_api_key = gpt_api_key or os.getenv("GPT_API_KEY")
        
        if not self.openai_api_key:
            print("[KeywordGenerator] Warning: No GPT API key provided. Keyword generation will be disabled.")
        
    def generate_keywords(self, question: str) -> List[str]:
        """
        Generate smart keywords for web search using GPT-4o-mini
        
        Args:
            question: User's question
            
        Returns:
            List of search keywords
        """
        if not self.openai_api_key:
            return [question]
            
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
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
                    {   
                        "role": "user",
                        "content": question
                    }
                ],
            )
            keywords = response.choices[0].message.content.strip()
            keywords = ast.literal_eval(keywords)
            return keywords
        except Exception as e:
            print(f"[KeywordGenerator] Error: {e}")
            return [question]
