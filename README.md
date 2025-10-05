# UniAdmission-ChatBot

![Python](https://img.shields.io/badge/python-v3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-green.svg)
![Qwen](https://img.shields.io/badge/Qwen3-4B-orange.svg)
![VLLM](https://img.shields.io/badge/vLLM-inference-red.svg)

Một chatbot AI hỗ trợ tư vấn tuyển sinh đại học thông minh.

🌐 **Demo trực tiếp**: [https://uniadmission.me](https://uniadmission.me)

## 📋 Mục lục

- [Tổng quan](#tổng-quan)
- [Tính năng chính](#tính-năng-chính)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Cài đặt](#cài-đặt)
- [Sử dụng](#sử-dụng)
- [Triển khai API model](#triển-khai-api)
- [Triển khai Kaggle](#triển-khai-kaggle)
- [API Documentation](#api-documentation)
- [Cấu hình nâng cao](#-cấu-hình-nâng-cao)

## 🎯 Tổng quan

UniAdmission-ChatBot là một hệ thống chatbot AI được thiết kế đặc biệt để hỗ trợ học sinh, phụ huynh và các bên liên quan trong việc tư vấn tuyển sinh đại học tại Việt Nam. 

Hệ thống sử dụng mô hình **Qwen3-4B được fine-tune** riêng cho nhiệm vụ tư vấn tuyển sinh, kết hợp với **intelligent routing system** để tự động lựa chọn giữa **Vector Database Search** và **Web Search** tùy theo loại câu hỏi.

### 🔍 **Smart Search Routing**
- **Vector Database**: Cho câu hỏi về điểm chuẩn, học phí, thông tin cụ thể của trường/ngành
- **Web Search**: Cho câu hỏi về tin tức, thông tin cập nhật, xu hướng tuyển sinh, thông tin 3 công khai

## ✨ Tính năng chính

- **🤖 Fine-tuned Qwen3-4B**: Mô hình AI được fine-tune đặc biệt cho lĩnh vực tư vấn tuyển sinh
- **🧠 Intelligent Search Routing**: Tự động phân tích câu hỏi và chọn phương pháp tìm kiếm tối ưu
  - **Vector Database Search**: Cho thông tin chuẩn về trường, ngành, điểm chuẩn
  - **Web Search**: Cho tin tức và thông tin cập nhật
- **📊 Vector Database**: Cơ sở dữ liệu vector chứa thông tin chi tiết của 200+ trường đại học
- **🚀 VLLM Inference**: Triển khai mô hình trên Kaggle với vLLM để tối ưu tốc độ
- **👤 Hệ thống xác thực**: Đăng nhập/đăng ký với session management
- **💬 Lịch sử hội thoại**: Lưu trữ và quản lý conversations với streaming response
- **🌐 Multi-source Integration**: Kết hợp dữ liệu từ vector DB, web search và fine-tuned model
- **📱 Responsive Web UI**: Giao diện thân thiện

## 🧩 Kiến trúc hệ thống

### Frontend (Web Application)
- **Web Interface**: HTML/CSS/JavaScript với chat interface
- **Templates**: Jinja2 cho login, register, chat pages
- **Real-time**: Streaming responses từ backend

### Backend API (FastAPI)
- **Authentication Routes**: JWT-based user management
- **Chat Routes**: Conversation handling với session management  
- **Intelligent Router**: Phân tích câu hỏi và chọn search strategy
- **Stream Management**: Quản lý real-time responses từ Kaggle

### AI/ML Pipeline
- **Qwen3-4B Fine-tuned**: Được training trên 1000+ Q&A tuyển sinh đại học tại Việt Nam
- **Smart Query Router**: Phân loại câu hỏi và chọn data source phù hợp
  ```python
  # Local DB: "Điểm chuẩn CNTT UET 2024?"
  # Web Search: "Xu hướng tuyển sinh 2025?"
  ```
- **Vector Database**: FAISS với multilingual-e5-small embeddings
- **Kaggle Deployment**: vLLM inference server với ngrok tunneling

### Data Architecture
- **Local DB Structure**:
  ```
  📁 vectordb/
  ├── 🏫 200+ universities × 4 sections each
  │   ├── thong_tin_chung (general info)
  │   ├── hoc_phi (tuition fees)  
  │   ├── diem_chuan (admission scores)
  │   └── tuyen_sinh (admission info)
  ```
- **Web Search**: Brave API + Google Custom Search
- **Cache System**: Vector cache với auto-refresh 15 phút

## 🚀 Cài đặt

### Yêu cầu hệ thống
- Python 3.9+ (ưu tiên Python 3.12.8)
- pip hoặc conda
- GPU (khuyến nghị cho việc chạy mô hình AI)

### Bước 1: Clone repository
```bash
git clone https://github.com/photienanh/UniAdmission-ChatBot.git
cd UniAdmission-ChatBot
```

### Bước 2: Tạo môi trường ảo
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### Bước 3: Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### Bước 4: Cấu hình môi trường
Tạo file `server.env` trong thư mục `app/`:
```env
NGROK_TOKEN=your_ngrok_token
JWT_SECRET_KEY=your_jwt_secret_key
# Server settings
HOST=0.0.0.0
PORT=8000
JWT_SECRET_KEY=your_secret_key_here
DATABASE_URL=your_database_url
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key
BRAVE_API_KEY=your_brave_api_key
```
Tạo file `worker.env` trong thư mục `app/`:
```
HUGGING_FACE_TOKEN=your_hugging_face_token

GEMINI_API_KEY=your_gemini_api_key
BRAVE_SEARCH_API_KEY=your_brave_api_key
OPENAI_API_KEY=your_openai_api_key
GOOGLE_SEARCH_API_KEY=your_google_api_key
GOOGLE_SEARCH_CX=your_google_search_cx

NGROK_TOKEN=your_ngrok_token
NGROK_TOKEN_1=your_ngrok_token_1
```

### Bước 5: Chạy ứng dụng
```bash
# Development mode
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
cd app  
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Ứng dụng sẽ chạy tại: `http://localhost:8000`

### Bước 6: Mở public server
Chạy file ngrok.py
## 🚀 Triển khai API model trên local
```bash
cd kaggle_dedicated
```
Chạy file `api_v3.py` (hoặc `api_v3.ipynb`)

## 🚀 Triển khai Kaggle

### Setup Kaggle Notebook
Dự án sử dụng Kaggle để deploy mô hình Qwen3-4B với vLLM:

1. **Upload notebook**: `kaggle_dedicatd/vllm_single_v3.ipynb`
2. **Cấu hình kết nối**:
   Đổi giá trị của `DOMAIN` trong block code đầu tiên thành url in ra khi chạy file `ngrok.py` (hoặc `https://uniadmission.me)`)
3. **Chạy notebook** - sẽ tự động:
   - Download code, dữ liệu, LoRA adapter từ server
   - Load Qwen3-4B + LoRA adapter
   - Khởi động vLLM inference server
   - Tạo ngrok tunnel cho public access
   - Connect với main server

### Kaggle Architecture
```python
# Kaggle deployment stack
Qwen3-4B (Base Model)
├── LoRA Fine-tuned Adapter (trên dữ liệu Q&A tuyển sinh)  
├── vLLM Inference Engine (fast generation)
├── Smart Query Router (vector vs web search)
├── ngrok Tunnel (public access)
└── FastAPI Integration (seamless connection)
```

### Model Performance
- **Base Model**: Qwen3-4B (4B parameters)
- **Fine-tuning**: LoRA on 1000+ Vietnamese admission Q&As
- **Inference Speed**: ~50 tokens/second trên Kaggle GPU
- **Context Length**: 32K tokens
- **Languages**: Vietnamese + English

## 📖 Sử dụng

### Web Interface
1. Truy cập [https://uniadmission.me](https://uniadmission.me) hoặc `http://localhost:8000`
2. Đăng ký/Đăng nhập tài khoản
3. Bắt đầu chat với bot:
   - **Vector DB queries**: "Điểm chuẩn CNTT UET 2024?", "Học phí ngành Y ĐHQGHN?"
   - **Web search queries**: "Thông báo tuyển sinh mới nhất", "Xu hướng ngành hot 2025"

### Ví dụ câu hỏi
```
🎯 Vector Database (thông tin chuẩn):
- "Điểm chuẩn ngành CNTT trường UET năm 2024?"
- "Học phí các ngành của ĐHBK Hà Nội?"  
- "Thông tin tuyển sinh trường FPT?"

🌐 Web Search (thông tin cập nhật):
- "Tin tức tuyển sinh đại học mới nhất?"
- "Xu hướng ngành nghề hot năm 2025?"
- "Thông báo tuyển sinh bổ sung?"
```

### Smart Routing Logic
Hệ thống tự động phân tích câu hỏi và chọn data source:
- **Từ khóa trường cụ thể** + **điểm chuẩn/học phí** → Vector DB
- **Câu hỏi chung** + **xu hướng/tin tức** → Web Search

### API Endpoints
- `POST /chat`: Gửi tin nhắn tới chatbot
- `GET /chat/{stream_id}`: Nhận streaming response
- `GET /sessions`: Lấy danh sách sessions của user
- `GET /session/{session_id}/messages`: Lấy lịch sử tin nhắn
- `DELETE /session/{session_id}`: Xóa session

## 📚 API Documentation

Sau khi chạy ứng dụng, bạn có thể truy cập:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🔧 Cấu hình nâng cao

### Fine-tuning Qwen3-4B
1. **Tạo training data**:
```bash
cd finetune
# Cấu hình API keys trong api_key.env
python make_data.py  # Tạo 1000+ Q&A pairs từ GPT-4
```

2. **Fine-tune model**:
   - Mở notebook `finetune/finetune_qwen3_4b.ipynb`
   - Chạy LoRA fine-tuning trên training data
   - Export adapter weights để deploy trên Kaggle

### Cập nhật Vector Database
```bash
cd vector_database/crawl

# Crawl dữ liệu mới từ các trường
python selenium_crawler.py -> python re_format.py -> python create_mapping.py

# Rebuild vector database
cd ..
python create_vector_db.py
# Tạo 800+ documents (200 trường × 4 sections)
```

**⭐ Nếu project này hữu ích cho bạn, hãy give star để ủng hộ nhé!**
