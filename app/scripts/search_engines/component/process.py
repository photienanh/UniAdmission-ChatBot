import tempfile
import os
import aiohttp
import asyncio
import traceback
import filetype
from typing import Literal

from ..schema import PreProcessedResult, ProcessedResult, FileContent, UrlContent
from .pdf_to_text import PDFProcessor
from .imge_to_text import ImageProcessor

class Processor:
    def __init__(self, session: aiohttp.ClientSession, timeout: float, concurrent_download: int = 16) -> None:
        self.timeout = aiohttp.ClientTimeout(timeout)
        self.session = session
        self.pdf_processor = PDFProcessor()
        self.image_processor = ImageProcessor()
        self._semaphore = asyncio.Semaphore(concurrent_download)
    def _clean_text(self, text: str) -> str:
        lines = text.splitlines()
        valid_lines = []
        for line in lines:
            stripped_line = line.strip()
            if len(stripped_line) > 5:
                valid_lines.append(line)
        return "\n".join(valid_lines)
    async def _pdf_task(self, content: bytes, parent_url: str, info: UrlContent) -> FileContent | None:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
                temp_pdf.write(content)
                temp_pdf_path = temp_pdf.name
            
            # File handle is now closed, we can safely process it
            pdf_docs = self.pdf_processor.process_pdf_to_documents(
                temp_pdf_path,
                parent_url=parent_url,
                url=info["url"]
            )
            text = self._clean_text("\n".join([pdf["text"] for pdf in pdf_docs]))
            result: FileContent = {
                **info,
                "parent_url":parent_url,
                "text": text
            }
            return result
        except Exception as e:
            print(f"Lỗi khi xử lý PDF {info['url']}: {e}")
        finally:
            try:
                del temp_pdf
                os.unlink(temp_pdf_path)  # Xóa file tạm thời
            except:
                pass
    async def _image_task(self, content: bytes, parent_url: str, info: UrlContent) -> FileContent | None:
        try:
            image_type = filetype.guess_extension(content) or 'jpg'
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{image_type}') as temp_image:
                temp_image.write(content)
                image_docs = self.image_processor.process_image_to_documents(
                    temp_image.name,
                    parent_url=info["url"],
                    url=info["url"]
                )
                text = self._clean_text("\n".join([pdf["text"] for pdf in image_docs]))
                result: FileContent = {
                    **info,
                    "parent_url":parent_url,
                    "text": text
                }
                return result
        except Exception as e:
            print(f"Lỗi khi xử lý Image {info['url']}: {e}")
        finally:
            try:
                del temp_image
                os.unlink(temp_image.name)  # Xóa file tạm thời #type:ignore
            except:
                pass
    async def _process_file(self, ssl: bool, headers, parent_url: str, info: UrlContent, file_type: Literal["image", "pdf"]) -> FileContent | None:
        async with self._semaphore: # Limit number of task (async task like network, thread write/read)
            try:
                async with self.session.get(info["url"], headers=headers, timeout=self.timeout, ssl=ssl) as response:
                    if response.ok:
                        if file_type == "pdf":
                            return await self._pdf_task(await response.read(), parent_url, info)
                        else:
                            return await self._image_task(await response.read(), parent_url, info)
                    else:
                        print(f"Không thể tải xuống {file_type} từ {info['url']}")
            except asyncio.TimeoutError:
                print(f"[Processor] Timeout: File: {info['url']}")
            except Exception as e:
                print(e)
                traceback.print_exc()
    async def __call__(self, input: PreProcessedResult) -> ProcessedResult | None:
        ssl = bool(os.getenv("WEB_SEARCH_SSL", "True"))
        # Implement here
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        pdf_tasks = []
        image_tasks = []
        for info in input["pdf_urls"]:
            task = asyncio.create_task(self._process_file(
                ssl=ssl, headers=headers, 
                parent_url=input["url"],
                info=info, 
                file_type="pdf"
            ))
            pdf_tasks.append(task)
        for info in input["image_urls"]:
            task = asyncio.create_task(self._process_file(
                ssl=ssl, headers=headers, 
                parent_url=input["url"],
                info=info, 
                file_type="image"
            ))
            image_tasks.append(task)
        pdf_contents, image_contents = await asyncio.gather(asyncio.gather(*pdf_tasks), asyncio.gather(*image_tasks))
        valid_pdfs: list[FileContent] = []
        valid_images: list[FileContent] = []
        for file_content in pdf_contents:
            if file_content is not None:
                valid_pdfs.append(file_content)
        for file_content in image_contents:
            if file_content is not None:
                valid_images.append(file_content)
        result: ProcessedResult = {
            "url": input["url"],
            "title": input["title"],
            "description": input["description"],
            "timestamp": input["timestamp"],
            "html": input["html"],
            "index": input["index"],
            "main_content": input["extracted_content"],
            "image_content": valid_images,
            "pdf_content": valid_pdfs
        }
        return result

# if __name__ == "__main__":
#     pdf_url = "https://www.hust.edu.vn/uploads/sys/ba-cong-khai/2023/bm17_cam-ket-chat-luong-dao-tao-nam-hoc-2023-2024.pdf"
#     pdf_processor = PDFProcessor()
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#     }
#     pdf_response = requests.get(pdf_url, headers=headers)
#     temp_pdf_path = None
    
#     if pdf_response.status_code == 200:
#         try:
#             with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
#                 temp_pdf.write(pdf_response.content)
#                 temp_pdf_path = temp_pdf.name
            
#             # File handle is now closed, we can safely process it
#             pdf_docs = pdf_processor.process_pdf_to_documents(
#                 temp_pdf_path,
#                 parent_url='',
#                 url=pdf_url
#             )
#         except Exception as e:
#             print(f"Lỗi khi xử lý PDF {pdf_url}: {e}")
#         finally:
#             try:
#                 del temp_pdf
#                 os.unlink(temp_pdf_path)  # Xóa file tạm thời
#             except:
#                 pass
#     else:
#         print(f"Không thể tải xuống PDF từ {pdf_url}")
#     print(pdf_docs[0]['text'][:500])