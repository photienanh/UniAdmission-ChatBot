import aiohttp
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
        k_pages: int, 
        search_k: int, 
        in_domain: bool = False, 
        engine_type: Literal["brave", "google"] = "brave",
        include_pdf: bool = False,
        include_image: bool = False,
        external_keywords: list[str] = None,
        rerank_pages = None
    ) -> list[ProcessedResult]:
        result: list[ProcessedResult] = []
        self.logger.enable = True
        
        # Generate smart keywords if enabled and no external keywords provided
        search_queries = [query]  # Default to original query
        if external_keywords and len(external_keywords) > 0:
            # Use external keywords provided by caller (e.g., web_search_keywords from app/)
            search_queries = external_keywords
        else:
            # Use original query for simple web search
            search_queries = [query]
                
        self.logger.start(f"Keywords: {search_queries}", k_pages, engine_type)
        
        
        # Collect results from all keywords (MULTIPLE SEARCHES) - BALANCED
        keyword_results_list = []  # Store results per keyword separately
        for i, search_query in enumerate(search_queries):
            try:
                print(f"[SearchPipeline] Searching with keyword {i+1}/{len(search_queries)}: '{search_query}'")
                keyword_results = await self.querier(search_query, search_k, in_domain, engine_type)
                keyword_results_list.append(keyword_results)
                
                # Add delay for API rate limiting (Brave API: 1 request/second)
                if i < len(search_queries) - 1:  # Don't sleep after the last query
                    await asyncio.sleep(1)
                    
            except Exception as e:
                print(f"[SearchPipeline] Search failed for keyword '{search_query}': {e}")
                keyword_results_list.append([])  # Add empty list for failed search
        
        # Balance results: take k_pages_per_keyword from each keyword
        balanced_results = []
        seen_urls = set()
        
        for i, keyword_results in enumerate(keyword_results_list):
            added_from_this_keyword = 0            
            for result in keyword_results:
                if result['url'] not in seen_urls and added_from_this_keyword < search_k:  # Use search_k to get more results
                    seen_urls.add(result['url'])
                    balanced_results.append(result)
                    added_from_this_keyword += 1
        
        # Apply rerank BEFORE crawling if callback provided
        if rerank_pages:
            balanced_results = rerank_pages(query, balanced_results)
        
        # Process balanced pages with detailed logging
        tasks = []
        for i, item in enumerate(balanced_results):
            async def task_f(index: int, search_result: SearchResult):
                async with self._semaphore:
                    try:
                        if search_result == None: 
                            return None
                        
                        self.logger.search(search_result, index)
                        
                        page_result = await self.downloader(search_result)
                        if page_result == None: 
                            return None
                        
                        self.logger.html(page_result, index)
                        preprocess_result = self.preprocessor(page_result)
                        if preprocess_result == None: 
                            return None
                        
                        self.logger.preprocessed(preprocess_result, index)
                        processed_result = await self.processor(preprocess_result, include_pdf, include_image)
                        if processed_result == None: 
                            return None
                        
                        self.logger.processed(processed_result, index)
                        return processed_result
                    except Exception as e:
                        traceback.print_exc()
                        return None
            task = asyncio.create_task(task_f(i, item))
            tasks.append(task)
            
        task_result = await asyncio.gather(*tasks)
        result = []
        successful_count = 0
        for item in task_result:
            if item is not None:
                result.append(item)
                successful_count += 1
        
        return result
    async def call_fast(
        self, 
        query: str, 
        k: int = 10, 
        in_domain: bool = False, 
        engine_type: Literal["brave", "google"] = "brave",
        include_pdf: bool = False,
        include_image: bool = False,
        external_keywords: list[str] = None,
        rerank_pages = None
    ) -> list[ProcessedResult]:
        # k is pages per keyword
        # Let _call handle the calculation after keyword generation
        return await self._call(
            query=query,
            k_pages=k,
            search_k=k*4,
            in_domain=in_domain,
            engine_type=engine_type,
            include_pdf=include_pdf,
            include_image=include_image,
            external_keywords=external_keywords,
            rerank_pages=rerank_pages
        )