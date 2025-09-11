import os, glob, shutil
import pytesseract
import filetype
from PIL import Image
import pymupdf4llm

from ..schema import FileContent
class PDFProcessor:
    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_PATH", "C:/Program Files/Tesseract-OCR/tesseract.exe")
        self.supported_formats = ['.pdf']
    def is_pdf_file(self, file_path: str) -> bool:
        try:
            kind = filetype.guess(file_path)
            return kind is not None and kind.extension == 'pdf'
        except:
            return file_path.lower().endswith('.pdf')

    def extract_text_from_image_of_pdf(self, images_dir: str) -> list:
        return []
        markdown_pages = []
        try:
            if not os.path.exists(images_dir):
                print(f"Directory {images_dir} does not exist.")
                return []

            image_files = glob.glob(os.path.join(images_dir, '*.png'))
            
            if not image_files:
                print(f"No images found in {images_dir}.")
                return []
            
            for i, img_path in enumerate(image_files):
                img = Image.open(img_path)
                
                text = pytesseract.image_to_string(img, lang='vie+eng')
                page_dict = {
                    'text': text,
                    'page_num': i + 1
                }
                markdown_pages.append(page_dict)

        except Exception as e:
            print(f'Error while extracting text from images: {e}')

        return markdown_pages

    def extract_text(self, file_path: str, include_metadata: bool = False) -> str:
        name_pdf = os.path.basename(file_path)
        name_pdf = os.path.splitext(name_pdf)[0]
        
        image_dir = os.path.join('images', name_pdf)
        os.makedirs(image_dir, exist_ok=True)
        
        try:
            md_content = pymupdf4llm.to_markdown(file_path,
                                                page_chunks=True,
                                                write_images=True,
                                                image_path=image_dir,
                                                image_format='png',
                                            )
            if os.path.exists(image_dir):
                md_image = self.extract_text_from_image_of_pdf(image_dir)
            else:
                md_image = []

            # remove 'images/{name_pdf}'
            try:
                shutil.rmtree(image_dir)
            except Exception as e:
                print(f'Error while removing images directory: {e}')

            if all(page['text'] for page in md_image):
                for page_text_based, page_image_based in zip(md_content, md_image):
                    page_text_based["text"] = page_image_based["text"]
                    
            content_parts = []
            
            # Handle different content formats
            if isinstance(md_content, str):
                # Simple string content
                content_parts.append(md_content)
                
            elif isinstance(md_content, list):
                if len(md_content) > 0 and isinstance(md_content[0], dict):
                    # PyMuPDF4LLM format - list of page dictionaries
                    for page in md_content:
                        page_content = []
                        
                        # Add page header
                        page_content.append("")
                        
                        # Add metadata if requested and available
                        if include_metadata and 'metadata' in page:
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
            content_str = "\n---\n".join(content_parts)
            return content_str
        
        except Exception as e:
            print(f"Lỗi khi đọc PDF với PyMuPDF: {e}")
            return ""

    def process_pdf_to_documents(self, file_path: str, parent_url: str = "", url: str = "") -> list[FileContent]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File không tồn tại: {file_path}")

        if not self.is_pdf_file(file_path):
            raise ValueError(f"File không phải là PDF: {file_path}")
        
        text = self.extract_text(file_path)

        if not text.strip():
            raise ValueError(f"Không thể trích xuất text từ PDF: {file_path}")

        title = os.path.basename(file_path)
        
        max_chunk_size = 8192 * 5  # Số ký tự tối đa trong một chunk
        contents = []
        
        if len(text) > max_chunk_size:
            paragraphs = text.split("\n\n")
            current_chunk = ""
            current_page = 1
            chunk_index = 1
            
            for paragraph in paragraphs:
                
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