import aiohttp
import os    
from typing import Literal, Any
import traceback
import asyncio

from .component import *
from .schema import *

class SearchPipeline:
    def __init__(self, 
            page_timeout: float, 
            file_timeout: float,
            concurrent_page: int = 4,
            concurrent_processor_download: int = 16
        ) -> None:
        self._kwargs: dict[str, Any] = {
            "page_timeout": page_timeout,
            "file_timeout": file_timeout,
            "concurrent_processor_download": concurrent_processor_download,
            "concurrent_page": concurrent_page
        }
    async def start(self):
        self._client = aiohttp.ClientSession()
        self.querier = WebQuery()
        self.downloader = PageDowloader(self._client, self._kwargs["page_timeout"])
        self.preprocessor = PreProcessor()
        self.processor = Processor(self._client, self._kwargs["file_timeout"], concurrent_download=self._kwargs["concurrent_processor_download"])
        self._semaphore = asyncio.Semaphore(self._kwargs["concurrent_page"])
        self.logger = Logger("web_search_logs")
    async def close(self):
        await self._client.close()
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
        self.logger.enable = True
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
            if item is not None and len(item["main_content"]) > 0:
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
    async def call_sequence(
        self, 
        query: str, 
        k: int = 10, 
        in_domain: bool = False, 
        engine_type: Literal["brave", "google"] = "brave",
        include_pdf: bool = False,
        include_image: bool = False
    ) -> list[ProcessedResult]:
        search_k = max(10, k) # Query at least 10
        result: list[ProcessedResult] = []
        self.logger.enable = True
        self.logger.start(query, k, engine_type)
        for search_result in await self.querier(query, search_k, in_domain, engine_type):
            try:
                if len(result) >= k: break # Break when reach target
                self.logger.count()
                if search_result == None: continue
                
                self.logger.search(search_result)
                page_result = await self.downloader(search_result)
                if page_result == None: continue
                
                self.logger.html(page_result)
                preprocess_result = self.preprocessor(page_result)
                if preprocess_result == None: continue
                
                self.logger.preprocessed(preprocess_result)
                processed_result = await self.processor(preprocess_result, include_pdf, include_image)
                if processed_result == None: continue
                
                self.logger.processed(processed_result)
                result.append(processed_result)
            except:
                traceback.print_exc()
        return result