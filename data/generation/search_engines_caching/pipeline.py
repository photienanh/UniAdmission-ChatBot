import aiohttp
import os    
from typing import Literal
import traceback
import asyncio
from openai import OpenAI

from .component import *
from .schema import *
from .cache import CacheSystem

INSTRUCTION = """Bạn là chuyên gia tạo từ khóa tìm kiếm thông minh. Nhiệm vụ: phân tích câu hỏi và tạo từ khóa giúp tìm được thông tin CĂN BẢN để LLM có thể suy luận ra câu trả lời.

CHIẾN LƯỢC TÌM KIẾM:

1. **Phân tích ý định câu hỏi**: Xác định thông tin gì cần thiết để trả lời
2. **Tìm nguồn thông tin gốc**: Thay vì tìm trực tiếp câu trả lời, tìm dữ liệu để suy luận
3. **Tối ưu từ khóa**: Dùng thuật ngữ chính thức, tên đầy đủ

VÍ DỤ THÔNG MINH:

Câu hỏi: "Số tiến sĩ trong viện trí tuệ nhân tạo UET là bao nhiêu?"
→ Cần: Danh sách giảng viên để đếm tiến sĩ
→ Từ khóa: danh sách giảng viên viện trí tuệ nhân tạo UET

Câu hỏi: "Điểm chuẩn ngành CNTT Bách Khoa 2024?"  
→ Cần: Bảng điểm chuẩn chính thức
→ Từ khóa: điểm chuẩn đại học Bách Khoa Hà Nội 2024

Câu hỏi: "Học phí ngành AI VNU-UET như thế nào?"
→ Cần: Bảng học phí chính thức  
→ Từ khóa: học phí đại học công nghệ VNU-UET 2024

Câu hỏi: "Chương trình đào tạo ngành CNTT có môn gì?"
→ Cần: Khung chương trình chi tiết
→ Từ khóa: chương trình đào tạo ngành công nghệ thông tin UET

Câu hỏi: "Đại học Bách khoa"
→ Cần: Thông tin Đại học Bách khoa
→ Từ khóa: đại học Bách khoa

Câu hỏi: "Tuyển sinh Đại học Bách khoa"
→ Cần: Thông tin tuyển sinh Đại học Bách khoa
→ Từ khóa: tuyển sinh đại học Bách khoa

NGUYÊN TẮC:
- Thêm năm 2025 nếu cần thông tin mới nhất
- Tìm "danh sách", "bảng", "chương trình" thay vì câu hỏi trực tiếp

Chỉ trả về từ khóa, không giải thích."""
SEARCH_PROMPT = """{user_message}
"""

class SearchPipeline:
    def __init__(self, 
            page_timeout: float, 
            file_timeout: float,
            concurrent_page: int = 4,
            concurrent_processor_download: int = 16
        ) -> None:
        self._client = aiohttp.ClientSession()
        self.querier = WebQuery()
        self.downloader = PageDowloader(self._client, page_timeout)
        self.preprocessor = PreProcessor()
        self.processor = Processor(self._client, file_timeout, concurrent_download=concurrent_processor_download)
        self._semaphore = asyncio.Semaphore(concurrent_page)
        self.logger = Logger("web_search_logs")
        self.cache = CacheSystem
        self.client = OpenAI(api_key=os.getenv("OPEN_AI_API_KEY"))
        CacheSystem.setup("sqlite:///cache/domain_brave_pdf.db")
    async def _extract_query(self, message: str):
        # HERE
        prompt = SEARCH_PROMPT.format(user_message=message)
        response = self.client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {"role": "system", "content": INSTRUCTION},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        result = response.choices[0].message.content or message
        print(f"[Query] {result}")
        return result
    async def close(self):
        await self._client.close()
        CacheSystem.close()
    async def _call(
        self, 
        query: str, 
        k: int, 
        search_k: int, 
        in_domain: bool = False, 
        engine_type: Literal["brave", "google"] = "brave",
        include_pdf: bool = False,
        include_image: bool = False
    ) -> list[ProcessedResult]:
        result: list[ProcessedResult] = []
        self.logger.start(query, k, engine_type)
        tasks = []
        for i, item in enumerate(await self.querier(query, search_k, in_domain, engine_type)):
            async def task_f(index: int, search_result: SearchResult):
                async with self._semaphore:
                    try:
                        if search_result == None: return
                        self.logger.search(search_result, index)
                        page_result = await self.downloader(search_result)
                        if page_result == None: return
                        
                        self.logger.html(page_result, index)
                        preprocess_result = self.preprocessor(page_result)
                        if preprocess_result == None: return
                        
                        self.logger.preprocessed(preprocess_result, index)
                        processed_result = await self.processor(preprocess_result, include_pdf, include_image)
                        if processed_result == None: return
                        
                        self.logger.processed(processed_result, index)
                        return processed_result
                    except:
                        traceback.print_exc()
            task = asyncio.create_task(task_f(i, item))
            tasks.append(task)
        task_result = await asyncio.gather(*tasks)
        result = []
        for item in task_result:
            if item is not None:
                result.append(item)
            if len(result) == k:
                break
        return result
    async def call_fast(
        self, 
        query: str, 
        k: int = 10, 
        in_domain: bool = False, 
        engine_type: Literal["brave", "google"] = "brave",
        include_pdf: bool = False,
        include_image: bool = False
    ) -> list[ProcessedResult]:
        return await self._call(
            query=query,
            k=k,
            search_k=k,
            in_domain=in_domain,
            engine_type=engine_type,
            include_pdf=include_pdf,
            include_image=include_image
        )
    async def call_k_safe(
        self, 
        query: str, 
        k: int = 10, 
        in_domain: bool = False, 
        engine_type: Literal["brave", "google"] = "brave",
        include_pdf: bool = False,
        include_image: bool = False
    ) -> list[ProcessedResult]:
        return await self._call(
            query=query,
            k=k,
            search_k=max(10, k),
            in_domain=in_domain,
            engine_type=engine_type,
            include_pdf=include_pdf,
            include_image=include_image
        )
    def _p_text(self, text: str) -> str:
        text = text.strip().lower()
        return text
    async def call_cache(
        self, 
        message: str, 
        k: int = 10, 
        in_domain: bool = False, 
        engine_type: Literal["brave", "google"] = "brave",
        include_pdf: bool = False,
        include_image: bool = False
    ) -> tuple[str, list[ProcessedResult]]:
        ori_message = message
        message = self._p_text(message)
        result = self.cache.get_by_user_query(message)
        if result == None:
            query = await self._extract_query(ori_message)
            query = self._p_text(query)
            result = self.cache.get_by_web_query(query)
            if result == None:
                print(f"[Search] Cache miss")
                result = await self.call_k_safe(
                    query, k, in_domain, engine_type, include_pdf, include_image
                )
            self.cache.cache_if_not_exists(message, query, result)
        else:
            query = self.cache.get_web_query(message)
        return (query, result)