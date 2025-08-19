from openai import OpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import json
from dotenv import load_dotenv
import os
from web_seach import get_context_from_web
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv("api_key.env")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def build_rag_context(question, retriever, k=10):
    docs = retriever.invoke(question, k=k)
    context = ""
    for doc in docs:
        context += f"{doc.metadata['school']} ({doc.metadata['school_symbol']})\n"
        context += doc.page_content + "\n" + 100*"-" + "\n"
    return context
    
def create_sample(question, client, retriever):
    if question.startswith("diem_chuan"):
        question = question.replace("diem_chuan ","")
        context = get_context_from_web(question, client, BRAVE_API_KEY)
    else:
        query = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Bạn là một AI viết lại truy vấn tìm kiếm RAG. Nhiệm vụ của bạn \
là phân tích câu hỏi và tạo ra một truy vấn tìm kiếm phù hợp để Retriever có thể tìm \
kiếm thông tin liên quan. LLM sẽ dựa vào thông tin được cung cấp để trả lời câu hỏi.\n \
CHIẾN LƯỢC TÌM KIẾM:\n \
1. **Phân tích ý định câu hỏi**: Xác định thông tin gì cần thiết để trả lời, xác định từ khóa cần thiết.\n \
2. **Tìm nguồn thông tin gốc**: Thay vì tìm trực tiếp câu trả lời, tìm dữ liệu để suy luận.\n \
Ví dụ:\n \
Câu hỏi: UET có bao nhiêu tiến sĩ?\n \
Cần: Danh sách giảng viên UET để đếm số lượng giảng viên là tiến sĩ.\n \
Output: Giảng viên UET.\n \
Chỉ đưa ra một truy vấn tìm kiếm phù hợp nhất, không cần trả lời câu hỏi."},
                        {"role": "user", "content": question}]
        ).choices[0].message.content.strip().replace('"', '').replace("'", "")
        context = build_rag_context(query, retriever)
    messages=[
        {"role": "system", "content": "Bạn là một AI tư vấn tuyển sinh đại học chuyên nghiệp. Hãy trả lời các câu hỏi một cách chính xác, hữu ích và thân thiện. Có thể sử dụng những thông tin được cung cấp để đưa ra câu trả lời hoặc lời khuyên tốt nhất."},
        {"role": "user", "content": f"""\nThông tin tham khảo:{context}\nCâu hỏi: {question}"""},
    ]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )
    messages.append({"role": "assistant", "content": response.choices[0].message.content.strip()})
    return {"messages": messages}

def make_data(question, client, retriever, i):
    messages = create_sample(question, client, retriever)
    with open("data.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(messages, ensure_ascii=False) + "\n")
    print(f"{i}.Completed: {question}")

if __name__ == "__main__":
    embedding = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-small")
    vectorstore = FAISS.load_local(
        "./faiss",
        embeddings=embedding,
        allow_dangerous_deserialization=True
    )
    retriever = vectorstore.as_retriever()

    client = OpenAI(api_key=OPENAI_API_KEY)
    with open('questions.txt', 'r', encoding='utf-8') as file:
        questions = [line.strip() for line in file]
    for i, question in enumerate(questions, 1):
        make_data(question, client, retriever, i)
