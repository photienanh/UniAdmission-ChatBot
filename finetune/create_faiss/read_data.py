import os
from typing import Iterator, TypedDict
from langchain.document_loaders import PyPDFLoader

NAME_MAPPING = {
    "aof": "Học viện Tài chính",
    "ftu": "Trường Đại học Ngoại thương",
    "haui": "Đại học Công nghiệp Hà Nội",
    "hcmus": "Trường Đại học Khoa học Tự nhiên - Đại học Quốc gia Thành phố Hồ Chí Minh",
    "hup": "Trường Đại học Dược Hà Nội",
    "hnue": "Trường Đại học Sư phạm Hà Nội",
    "huce": "Trường Đại học Xây dựng Hà Nội",
    "hust": "Đại học Bách khoa Hà Nội",
    "neu": "Đại học Bách khoa Hà Nội",
    "ptit": "Học viện Công nghệ Bưu chính Viễn thông",
    "ueb": "Trường Đại học Kinh tế - Đại học Quốc gia Hà Nội",
    "ued": "Trường Đại học Giáo dục - Đại học Quốc gia Hà Nội",
    "uet": "Trường Đại học Công nghệ - Đại học Quốc gia Hà Nội",
    "ulis": "Trường Đại học Ngoại ngữ - Đại học Quốc gia Hà Nội",
    "ussh": "Trường Đại học Khoa học Xã hội và Nhân văn - Đại học Quốc gia Hà Nội",
    "utc": "Đại học Giao thông vận tải"
}

class FileContent(TypedDict):
    school_name: str
    school_symbol: str
    text: str
    
def read_data(folder_path: str) -> Iterator[FileContent]:
    for school_symbol in os.listdir(folder_path):
        school_dir = os.path.join(folder_path, school_symbol)
        # Kiểm tra nếu là thư mục
        if not os.path.isdir(school_dir):
            continue
            
        # Lấy tên trường từ mapping, bỏ qua nếu không có trong mapping
        school_name = NAME_MAPPING.get(school_symbol)
        if not school_name:
            print(f"Không tìm thấy tên trường cho mã: {school_symbol}")
            continue
            
        # Đọc tất cả file PDF trong thư mục của trường
        for file_name in os.listdir(school_dir):
            if file_name.lower().endswith('.pdf'):
                file_path = os.path.join(school_dir, file_name)
                try:
                    # Sử dụng PyPDFLoader để đọc file PDF
                    loader = PyPDFLoader(file_path)
                    documents = loader.load()
                    
                    # Ghép nội dung từ tất cả các trang
                    text = "\n".join([doc.page_content for doc in documents])
                    
                    content: FileContent = {
                        "school_name": school_name,
                        "school_symbol": school_symbol,
                        "text": text
                    }
                    yield content
                    print(f"Đã đọc thành công: {file_path}")
                except Exception as e:
                    print(f"Lỗi khi đọc file {file_path}: {e}")
                    continue