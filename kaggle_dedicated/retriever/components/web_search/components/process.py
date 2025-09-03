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
                "file_type": "pdf",
                "parent_url":parent_url,
                "text": text,
                "title": info["title"],
                "url": info["url"]
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
                    "file_type": "image",
                    "parent_url":parent_url,
                    "text": text,
                    "title": info["title"],
                    "url": info["url"]
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
    async def __call__(self, input: PreProcessedResult, include_pdf: bool, include_image: bool) -> ProcessedResult | None:
        ssl = os.getenv("WEB_SEARCH_SSL", "True").lower() in ("true", "1")
        # Implement here
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        file_tasks = []
        for info in input["file_urls"]:
            if info["url_type"] == "pdf" and include_pdf:
                task = asyncio.create_task(self._process_file(
                    ssl=ssl, headers=headers, 
                    parent_url=input["url"],
                    info=info, 
                    file_type="pdf"
                ))
                file_tasks.append(task)
            elif info["url_type"] == "image" and include_image:
                task = asyncio.create_task(self._process_file(
                    ssl=ssl, headers=headers, 
                    parent_url=input["url"],
                    info=info, 
                    file_type="image"
                ))
                file_tasks.append(task)
        file_contents = await asyncio.gather(*file_tasks)
        valid_files: list[FileContent] = []
        for file_content in file_contents:
            if file_content is not None:
                valid_files.append(file_content)
        result: ProcessedResult = {
            "url": input["url"],
            "title": input["title"],
            "description": input["description"],
            "timestamp": input["timestamp"],
            "html": input["html"],
            "index": input["index"],
            "main_content": input["extracted_content"],
            "file_contents": valid_files
        }
        return result