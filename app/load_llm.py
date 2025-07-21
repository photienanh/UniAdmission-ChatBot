from dotenv import load_dotenv
import os
import google.generativeai as genai
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def initialize_rag():
    embedding = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-small", cache_folder='./cache')
    vectorstore = Chroma(persist_directory="../vector_db", embedding_function=embedding)
    retriever = vectorstore.as_retriever()
    return retriever

def build_rag_prompt(question: str, retriever, k=3):
    # Truy xuất các chunk văn bản liên quan
    docs = retriever.invoke(question, k=k)
    context = "\n\n".join([doc.page_content for doc in docs])
    
    # Tạo prompt có chèn ngữ cảnh
    prompt = f"""
Bạn là một AI tư vấn tuyển sinh đại học, dựa vào hiểu biết của mình, có thể sử dụng kèm theo những thông tin sau đây, hãy trả lời câu hỏi hoặc đưa ra tư vấn.

Thông tin được cung cấp:
{context}

Câu hỏi:
{question}

Trả lời:
"""
    return prompt

def initialize_llm():
    load_dotenv('gemini_api_key.env')
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.0-flash-lite-preview-02-05")
    return model

def ask_gemini(question, model, retriever):
    prompt = build_rag_prompt(question, retriever)
    response = model.generate_content(prompt)
    return {"response": response.text}