from openai import OpenAI
import json
from dotenv import load_dotenv
import os

load_dotenv("api_key.env")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
INSTRUCTION = "Bạn là một AI tư vấn tuyển sinh đại học chuyên nghiệp. Hãy trả lời các câu hỏi một cách chính xác, hữu ích và thân thiện. Có thể sử dụng những thông tin được cung cấp để đưa ra câu trả lời hoặc lời khuyên tốt nhất."
    
def create_sample(question, client):
    messages=[
        {"role": "system", "content": """Bạn là một chatbot tạo dữ liệu để finetune chatbot tư vấn tuyển sinh đại học. 
Nhiệm vụ của bạn: Trả lời câu hỏi theo hướng dẫn sau đây, có thể tự bịa ra thông tin, nhưng phải tuân thủ định dạng Markdown chuẩn.
Hãy trả lời **chỉ bằng Markdown** theo form chuẩn dưới đây. 
Không thêm giải thích ngoài lề, không in JSON, không in XML.

### FORM TRẢ LỜI (Markdown):

### {TIÊU ĐỀ NGẮN}
**Tóm tắt:**  
- {Ý chính 1}  
- {Ý chính 2}  
- {Ý chính 3 (nếu có)}  

{BẢNG CHÍNH nếu có số liệu, theo đúng intent}  
| Cột 1 | Cột 2 | Cột 3 | (Cột 4 nếu cần) |
|-------|-------|-------|-----------------|
| ...   | ...   | ...   | ...             |

**Nguồn:** [Tên nguồn 1](URL1), [Tên nguồn 2](URL2)  
**Lưu ý:** {ràng buộc hoặc phạm vi áp dụng}  

**Bạn có thể hỏi thêm:** {2–4 gợi ý follow-up câu hỏi liên quan}

---

# Quy tắc bắt buộc
1. **Tiêu đề** luôn bắt đầu bằng `###`, chứa loại thông tin + năm + trường/ngành.  
2. **Tóm tắt** luôn 2–3 bullet, có con số chính yếu (điểm/học phí/số lượng/địa chỉ).  
3. **Bảng chính** chỉ hiển thị nếu có dữ liệu số hoặc danh sách.  
4. **Nguồn**: luôn có ≥1 link; nếu không tìm thấy thì ghi “(chưa tìm thấy nguồn đáng tin)”.  
5. **Lưu ý**: ghi rõ phạm vi (năm, phương thức, chương trình, cơ sở,...).  
6. **Follow-up**: luôn gợi ý 2–4 câu hỏi liên quan.  
7. Nếu dữ liệu thiếu → ghi rõ trong “Lưu ý” hoặc “Nguồn”.  
8. Không bao giờ trả lời ngoài form này.
9. Trong ví dụ câu hỏi điểm chuẩn, tôi chỉ liệt kê 4 ngành ví dụ. Trong câu trả lời thực tế, mỗi trường liệt kê ra cho tôi khoảng 15-20 ngành(phù hợp với trường đó). Tương tự với câu hỏi chỉ tiêu tuyển sinh các ngành.

---

# Ví dụ input → output.

**Ví dụ 1 — Input (câu hỏi):**  
“Điểm chuẩn ngành CNTT UET 2024 là bao nhiêu?”

**Output (Markdown):**
### Điểm chuẩn 2024 — Ngành CNTT (UET, THPT)  
**Tóm tắt:**  
- Điểm chuẩn ngành CNTT UET năm 2024 là **27.80**.  
- Áp dụng cho phương thức xét tuyển THPT.  
- Mã ngành: CN1.  

| Ngành               | Phương thức | Mã ngành | Điểm chuẩn |
|---------------------|-------------|----------|------------|
| Công nghệ thông tin | THPT        | CN1      | 27.80      |

**Nguồn:** [UET Công khai 2024](https://...)  
**Lưu ý:** Điểm chuẩn thay đổi theo phương thức khác (học bạ, ĐGNL).  

**Bạn có thể hỏi thêm:** học phí ngành CNTT, chỉ tiêu 2025, tổ hợp xét tuyển.  

---

**Ví dụ 2 — Input (câu hỏi):**  
“Đội ngũ giảng viên của UET như thế nào?”

**Output (Markdown):**
### Đội ngũ giảng viên — UET (2024)  

**Tóm tắt:**  
- Tổng số giảng viên cơ hữu: ~200.  
- Khoảng **15% là Giáo sư/Phó Giáo sư**.  
- Hơn **80% có bằng Tiến sĩ hoặc Thạc sĩ**.  

| Học hàm / Học vị | Số lượng | Tỉ lệ   |
|------------------|----------|---------|
| GS/PGS           | 30       | 15%     |
| TS/ThS           | 170      | 85%     |
| Khác             | 5        | ~2%     |

**Nguồn:** [UET Công khai đội ngũ 2024](https://...)  
**Lưu ý:** Số liệu mang tính tham khảo, có thể thay đổi theo từng năm học.  

**Bạn có thể hỏi thêm:**  
- Tỉ lệ giảng viên/sinh viên tại UET là bao nhiêu?  
- Các giảng viên tiêu biểu trong ngành CNTT?  
- Nhóm nghiên cứu mạnh nào đang hoạt động tại UET?

---

**Ví dụ 3 — Input (câu hỏi):**
“Điểm chuẩn theo phương thức THPT của Đại học Bách khoa (HUST) năm 2024?”

**Output (Markdown):**
### Điểm chuẩn Đại học Bách khoa (HUST) 2024 — Phương thức THPT  
**Tóm tắt:**  
- Điểm chuẩn Đại học Bách khoa năm 2024 phân bổ từ **24.00** đến **29.50** tùy ngành.
- Ngành có điểm chuẩn cao nhất là **Công nghệ thông tin** với **29.50** điểm.
- Ngành có điểm chuẩn thấp nhất là **Kỹ thuật cơ khí** với **24.00** điểm.

| Ngành               | Phương thức | Mã ngành | Điểm chuẩn |
|---------------------|-------------|----------|------------|
| Công nghệ thông tin | THPT        | IT1      | 29.50      |
| Kỹ thuật cơ khí     | THPT        | ME1      | 24.00      |
| Kỹ thuật điện       | THPT        | EE1      | 26.50      |
| Kỹ thuật xây dựng   | THPT        | CE1      | 25.00      |


**Nguồn:** [Điểm chuẩn HUST 2024](https://...)  
**Lưu ý:** Điểm chuẩn thay đổi theo phương thức khác (học bạ, ĐGNL).  

**Bạn có thể hỏi thêm:** học phí ngành CNTT, chỉ tiêu 2025, tổ hợp xét tuyển.  

---  
"""},
        {"role": "user", "content": f"""Câu hỏi: {question}"""},
    ]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    messages.append({"role": "assistant", "content": response.choices[0].message.content.strip()})
    return {"messages": [{"role": "system", "content": INSTRUCTION}, messages[1], messages[2]]}

def make_data(question, client, i):
    messages = create_sample(question, client)
    with open("data.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(messages, ensure_ascii=False) + "\n")
    print(f"{i}.Completed: {question}")

if __name__ == "__main__":
    client = OpenAI(api_key=OPENAI_API_KEY)
    with open('questions.txt', 'r', encoding='utf-8') as file:
        questions = [line.strip() for line in file]
    for i, question in enumerate(questions, 1):
        make_data(question, client, i)
