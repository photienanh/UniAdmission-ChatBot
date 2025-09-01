from typing import List, Dict, Any
import os
import cv2
import pytesseract
import numpy as np
import filetype
from PIL import Image

from ..schema import FileContent
class ImageProcessor:
    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_PATH", "C:/Program Files/Tesseract-OCR/tesseract.exe")
        self.supported_formats = ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp', 'svg']
        # Cấu hình OCR cho tiếng Việt
        self.ocr_config = '--oem 3 --psm 6 -l vie+eng'
        # Kiểm tra và cài đặt thêm các ngôn ngữ nếu cần
        self._check_tesseract_languages()

    def _check_tesseract_languages(self):
        """Kiểm tra các gói ngôn ngữ của Tesseract đã được cài đặt chưa"""
        try:
            languages = pytesseract.get_languages()
            
            if 'vie' not in languages:
                self.ocr_config = '--oem 3 --psm 6 -l eng'
        except Exception as e:
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
        
        # 5. Phiên bản với adaptive threshold
        adaptive_thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                               cv2.THRESH_BINARY, 11, 2)
        preprocessed_versions.append(("adaptive", adaptive_thresh))

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

    def process_image_to_documents(self, image_path: str, parent_url: str = "", url: str = "") -> List[FileContent]:
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