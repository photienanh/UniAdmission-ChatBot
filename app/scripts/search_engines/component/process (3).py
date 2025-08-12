import requests
from typing import List, Dict, Any
import os
import cv2
import pytesseract
import numpy as np
import filetype
from PIL import Image
import tempfile
import pymupdf4llm

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' 

from ..engines import PreProcessedResult, ProcessedResult, Content

class PDFProcessor:
    def __init__(self):
        self.supported_formats = ['.pdf']

    def is_pdf_file(self, file_path: str) -> bool:
        try:
            kind = filetype.guess(file_path)
            return kind is not None and kind.extension == 'pdf'
        except:
            return file_path.lower().endswith('.pdf')

    def extract_text(self, file_path: str, include_metadata: bool = False) -> str:        
        try:
            md_content = pymupdf4llm.to_markdown(file_path,page_chunks=True)
            content_parts = []
            
            # Handle different content formats
            if isinstance(md_content, str):
                # Simple string content
                content_parts.append(md_content)
                
            elif isinstance(md_content, list):
                if len(md_content) > 0 and isinstance(md_content[0], dict):
                    # PyMuPDF4LLM format - list of page dictionaries
                    for i, page in enumerate(md_content):
                        page_content = []
                        
                        # Add page header
                        page_content.append(f"# Page {i + 1}")
                        page_content.append("")
                        
                        # Add metadata if requested and available
                        if include_metadata and i == 0 and 'metadata' in page:
                            metadata = page['metadata']
                            page_content.append("## Document Metadata")
                            for key, value in metadata.items():
                                if value:  # Only include non-empty values
                                    page_content.append(f"- **{key.title()}**: {value}")
                            page_content.append("")
                        
                        # Add main text content
                        if 'text' in page and page['text']:
                            page_content.append(page['text'])
                        
                        # Add table of contents if available
                        if 'toc_items' in page and page['toc_items']:
                            page_content.append("\n## Table of Contents")
                            for toc_item in page['toc_items']:
                                page_content.append(f"- {toc_item}")
                        
                        content_parts.append("\n".join(page_content))
                        
                else:
                    # List of strings
                    content_parts.extend(md_content)
            
            # Join all content with page separators
            content_str = "\n\n---\n\n".join(content_parts)
            return content_str
        
        except Exception as e:
            print(f"Lỗi khi đọc PDF với PyMuPDF: {e}")
            return ""

    def process_pdf_to_documents(self, file_path: str, parent_url: str = "", url: str = "") -> List[Content]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File không tồn tại: {file_path}")

        if not self.is_pdf_file(file_path):
            raise ValueError(f"File không phải là PDF: {file_path}")
        
        text = self.extract_text(file_path)

        if not text.strip():
            raise ValueError(f"Không thể trích xuất text từ PDF: {file_path}")

        title = os.path.basename(file_path)
        
        max_chunk_size = 8192  # Số ký tự tối đa trong một chunk
        contents = []
        
        if len(text) > max_chunk_size:
            paragraphs = text.split("\n\n")
            current_chunk = ""
            current_page = 1
            chunk_index = 1
            
            for paragraph in paragraphs:
                if "--- Trang " in paragraph:
                    try:
                        current_page = int(paragraph.split("--- Trang ")[1].split(" ---")[0])
                        current_chunk += paragraph + "\n\n"
                        continue
                    except:
                        pass
                
                if len(current_chunk) + len(paragraph) > max_chunk_size:
                    # Tạo một Content object mới với chunk hiện tại
                    chunk_title = f"{title} - Phần {chunk_index} (Trang ~{current_page})"
                    contents.append({
                        "title": chunk_title,
                        "parent_url": parent_url,
                        "url": url,
                        "text": current_chunk.strip()
                    })
                    chunk_index += 1
                    current_chunk = paragraph + "\n\n"
                else:
                    current_chunk += paragraph + "\n\n"
            
            # Thêm chunk cuối cùng nếu còn
            if current_chunk.strip():
                chunk_title = f"{title} - Phần {chunk_index} (Trang ~{current_page})"
                contents.append({
                    "title": chunk_title,
                    "parent_url": parent_url,
                    "url": url,
                    "text": current_chunk.strip()
                })
        else:
            # Nếu PDF ngắn, tạo một Content duy nhất
            contents = [{
                "title": title,
                "parent_url": parent_url,
                "url": url,
                "text": text
            }]

        return contents
    
class ImageProcessor:
    def __init__(self):
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        # Cấu hình OCR cho tiếng Việt
        self.ocr_config = '--oem 3 --psm 6 -l vie+eng'

        # Uncomment và chỉnh sửa đường dẫn nếu cần thiết (cho Windows)
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        
        # Kiểm tra và cài đặt thêm các ngôn ngữ nếu cần
        self._check_tesseract_languages()

    def _check_tesseract_languages(self):
        """Kiểm tra các gói ngôn ngữ của Tesseract đã được cài đặt chưa"""
        try:
            # Kiểm tra xem Tesseract có hoạt động không
            languages = pytesseract.get_languages()
            print(f"Tesseract languages: {languages}")
            
            # Nếu Vietnamese (vie) không có trong danh sách, hiển thị hướng dẫn cài đặt
            if 'vie' not in languages:
                print("CẢNH BÁO: Gói ngôn ngữ tiếng Việt cho Tesseract OCR chưa được cài đặt!")
                print("Hướng dẫn cài đặt:")
                print("- Windows: Tải và cài đặt gói vie.traineddata vào thư mục tessdata")
                print("- Linux: sudo apt-get install tesseract-ocr-vie")
                print("- macOS: brew install tesseract-lang")
                
                # Sử dụng tiếng Anh làm ngôn ngữ mặc định nếu không có tiếng Việt
                self.ocr_config = '--oem 3 --psm 6 -l eng'
        except Exception as e:
            print(f"Cảnh báo: Không thể kiểm tra ngôn ngữ Tesseract: {e}")
            print("Sử dụng cấu hình OCR mặc định")
            self.ocr_config = '--oem 3 --psm 6'

    def is_image_file(self, file_path: str) -> bool:
        try:
            kind = filetype.guess(file_path)
            return kind is not None and any(kind.extension.lower() in ext for ext in self.supported_formats)
        except:
            return any(file_path.lower().endswith(ext) for ext in self.supported_formats)

    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Tiền xử lý hình ảnh để cải thiện độ chính xác OCR
        """
        # Đọc ảnh bằng OpenCV
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Không thể đọc hình ảnh: {image_path}")

        # Tạo nhiều phiên bản tiền xử lý khác nhau
        preprocessed_versions = []
        
        # 1. Phiên bản grayscale cơ bản
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        preprocessed_versions.append(("basic_gray", gray))
        
        # 2. Phiên bản tăng contrast
        contrast = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
        preprocessed_versions.append(("contrast", contrast))
        
        # 3. Phiên bản làm mịn
        denoised = cv2.medianBlur(contrast, 3)
        preprocessed_versions.append(("denoised", denoised))
        
        # 4. Phiên bản nhị phân (binary)
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        preprocessed_versions.append(("binary", thresh))
        
        # 5. Phiên bản nhị phân đảo ngược (nghịch đảo)
        thresh_inv = cv2.bitwise_not(thresh)
        preprocessed_versions.append(("binary_inv", thresh_inv))
        
        # 6. Phiên bản với adaptive threshold
        adaptive_thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                               cv2.THRESH_BINARY, 11, 2)
        preprocessed_versions.append(("adaptive", adaptive_thresh))
        
        # 7. Phiên bản resize (tăng kích thước)
        h, w = gray.shape
        scaled = cv2.resize(gray, (w*2, h*2), interpolation=cv2.INTER_CUBIC)
        preprocessed_versions.append(("scaled", scaled))

        return preprocessed_versions

    def extract_text_from_image(self, image_path: str) -> Dict[str, Any]:
        """
        Trích xuất text từ hình ảnh bằng OCR với nhiều phương pháp tiền xử lý khác nhau
        và chọn kết quả tốt nhất
        """
        try:
            processed_versions = self.preprocess_image(image_path)
            
            best_text = ""
            best_confidence = 0
            best_data = None
            best_method = ""
            
            # Thử OCR với từng phiên bản xử lý
            for method_name, processed_image in processed_versions:
                try:
                    # Thử OCR
                    text = pytesseract.image_to_string(processed_image, config=self.ocr_config)
                    data = pytesseract.image_to_data(processed_image, config=self.ocr_config, output_type=pytesseract.Output.DICT)
                    
                    # Tính confidence score trung bình
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    
                    # Chọn kết quả tốt nhất dựa trên confidence và độ dài text
                    if (len(text) > len(best_text) and avg_confidence >= best_confidence * 0.8) or (avg_confidence > best_confidence and len(text) >= len(best_text) * 0.8):
                        best_text = text
                        best_confidence = avg_confidence
                        best_data = data
                        best_method = method_name
                        
                except Exception as method_err:
                    print(f"Lỗi với phương pháp {method_name}: {method_err}")
                    continue

            # Nếu không phương pháp nào hoạt động, thử OCR với ảnh gốc
            if not best_text:
                print("Thử OCR với ảnh gốc...")
                with Image.open(image_path) as img:
                    best_text = pytesseract.image_to_string(img, config=self.ocr_config)
                    best_method = "original"

            # Lấy thông tin hình ảnh
            with Image.open(image_path) as img:
                width, height = img.size
                format_type = img.format

            metadata = {
                "image_size": (width, height),
                "format": format_type,
                "avg_confidence": best_confidence,
                "processing_method": best_method,
                "total_words": len(best_text.split()) if best_text else 0
            }

            return {
                "text": best_text.strip(),
                "metadata": metadata,
                "raw_data": best_data
            }

        except Exception as e:
            print(f"Lỗi khi xử lý OCR: {e}")
            return {"text": "", "metadata": {"error": str(e)}, "raw_data": {}}

    def process_image_to_documents(self, image_path: str, parent_url: str = "", url: str = "") -> List[Content]:
        """
        Xử lý hình ảnh thành Content objects
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"File không tồn tại: {image_path}")

        if not self.is_image_file(image_path):
            raise ValueError(f"File không phải là hình ảnh: {image_path}")

        # Trích xuất text bằng OCR
        result = self.extract_text_from_image(image_path)
        text = result["text"]
        ocr_metadata = result["metadata"]

        if not text.strip():
            print(f"Không thể trích xuất text từ hình ảnh: {image_path}")
            text = f"[Hình ảnh không có text có thể đọc được: {os.path.basename(image_path)}]"

        # Tạo title từ file name
        title = os.path.basename(image_path)

        # Tạo Content object
        content = {
            "title": title,
            "parent_url": parent_url,
            "url": url,
            "text": text
        }

        return [content]

class Processor:
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        self.pdf_processor = PDFProcessor()
        self.image_processor = ImageProcessor()
    
    def __call__(self, input: PreProcessedResult) -> ProcessedResult | None:
        # Implement here
        pdf_content = []
        image_content = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        for pdf_url_content in input['pdf_urls']:
            pdf_url = pdf_url_content['url']
            pdf_response = requests.get(pdf_url, headers=headers)
            temp_pdf_path = None
            if pdf_response.status_code == 200:
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                        temp_pdf.write(pdf_response.content)
                        temp_pdf_path = temp_pdf.name
                    
                    # File handle is now closed, we can safely process it
                    pdf_docs = self.pdf_processor.process_pdf_to_documents(
                        temp_pdf_path,
                        parent_url=input['url'],
                        url=pdf_url
                    )
                    pdf_content.extend(pdf_docs)
                except Exception as e:
                    print(f"Lỗi khi xử lý PDF {pdf_url}: {e}")
                finally:
                    try:
                        del temp_pdf
                    except:
                        pass
            else:
                print(f"Không thể tải xuống PDF từ {pdf_url}")
        
        # Xử lý hình ảnh
        for image_url_content in input['image_urls']:
            image_url = image_url_content['url']
            image_response = requests.get(image_url, headers=headers)
            if image_response.status_code == 200:
                try:
                    image_type = filetype.guess_extension(image_response.content) or 'jpg'
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{image_type}') as temp_image:
                        temp_image.write(image_response.content)
                        image_docs = self.image_processor.process_image_to_documents(
                            temp_image.name,
                            parent_url=input['url'],
                            url=image_url
                        )
                        image_content.extend(image_docs)
                except Exception as e:
                    print(f"Lỗi khi xử lý Image {image_url}: {e}")
                finally:
                    try:
                        del temp_image
                    except:
                        pass
            else:
                print(f"Không thể tải xuống hình ảnh từ {image_url}")
        
        result: ProcessedResult = {
            "url": input["url"],
            "title": input["title"],
            "description": input["description"],
            "timestamp": input["timestamp"],
            "html": input["html"],
            "index": input["index"],
            "main_content": input["extracted_content"],
            "image_content": image_content,
            "pdf_content": pdf_content
        }
        return result
    
# if __name__ == "__main__":
#     image_processor = ImageProcessor()
#     pdf_processor = PDFProcessor()
    
#     pdf_content = []
#     image_content = []
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#     }
#     input = {
#         'pdf_urls': [{'url': 'https://images.tuyensinh247.com/picture/2025/0625/01thong-tin-ts-hus-ban-hanh-cung-qd-dieu-chinh-final-ht-ky.pdf', 'title': 'Thông tin tuyển sinh'}],
#         'image_urls': [{'url': 'https://i.sstatic.net/OmdTj.png', 'title': 'Hình ảnh'}],
#         'url': 'https://example.com'
#     }
    
#     # Xử lý PDF
#     for pdf_url_content in input['pdf_urls']:
#         pdf_url = pdf_url_content['url']
#         pdf_response = requests.get(pdf_url, headers=headers)
#         temp_pdf_path = None
#         if pdf_response.status_code == 200:
#             try:
#                 with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
#                     temp_pdf.write(pdf_response.content)
#                     temp_pdf_path = temp_pdf.name
                
#                 # File handle is now closed, we can safely process it
#                 pdf_docs = pdf_processor.process_pdf_to_documents(
#                     temp_pdf_path,
#                     parent_url=input['url'],
#                     url=pdf_url
#                 )
#                 pdf_content.extend(pdf_docs)
#             except Exception as e:
#                 print(f"Lỗi khi xử lý PDF {pdf_url}: {e}")
#             finally:
#                 try:
#                     os.unlink(temp_pdf.name)
#                 except:
#                     pass
#         else:
#             print(f"Không thể tải xuống PDF từ {pdf_url}")
    
#     # Xử lý hình ảnh
#     for image_url_content in input['image_urls']:
#         image_url = image_url_content['url']
#         image_response = requests.get(image_url, headers=headers)
#         if image_response.status_code == 200:
#             try:
#                 image_type = filetype.guess_extension(image_response.content) or 'jpg'
#                 with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{image_type}') as temp_image:
#                     temp_image.write(image_response.content)
#                     image_docs = image_processor.process_image_to_documents(
#                         temp_image.name,
#                         parent_url=input['url'],
#                         url=image_url
#                     )
#                     image_content.extend(image_docs)
#             except Exception as e:
#                 print(f"Lỗi khi xử lý PDF {pdf_url}: {e}")
#             finally:
#                 try:
#                     os.unlink(temp_image.name)
#                 except:
#                     pass
#         else:
#             print(f"Không thể tải xuống hình ảnh từ {image_url}")
    
#     print(f"pdf content: {pdf_content[:200]}")
#     print(f"image content: {image_content[:200]}")
