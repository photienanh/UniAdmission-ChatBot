import aiohttp
import os    
from typing import Literal, Any
import traceback
import asyncio

from .component import *
from .schema import *
from .keyword_generator_vector import generate_search_keywords

class SearchPipeline:
    def __init__(self, 
            page_timeout: float, 
            file_timeout: float,
            concurrent_page: int = 4,
            concurrent_processor_download: int = 16,
            use_internal_generation: bool = True,
            gpt_api_key: str = None
        ) -> None:
        self._kwargs: dict[str, Any] = {
            "page_timeout": page_timeout,
            "file_timeout": file_timeout,
            "concurrent_processor_download": concurrent_processor_download,
            "concurrent_page": concurrent_page
        }
        self.use_internal_generation = use_internal_generation
        self.gpt_api_key = gpt_api_key
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
        include_image: bool = False,
        external_keywords: list[str] = None
    ) -> list[ProcessedResult]:
        result: list[ProcessedResult] = []
        self.logger.enable = True
        
        # Generate smart keywords if enabled and no external keywords provided
        search_queries = [query]  # Default to original query
        if external_keywords and len(external_keywords) > 0:
            # Use external keywords provided by caller (e.g., QueryRewrite)
            search_queries = external_keywords
        elif self.use_internal_generation:
            try:
                # Set GPT API key in environment if provided
                if self.gpt_api_key:
                    os.environ["GPT_API_KEY"] = self.gpt_api_key
                
                search_strategy = generate_search_keywords(query)
                
                # Extract keywords based on search type
                if search_strategy.get("type_search") == "web_search":
                    generated_keywords = search_strategy.get("key_word", [query])
                    if generated_keywords and len(generated_keywords) > 0:
                        search_queries = generated_keywords
                else:
                    # For vector_db search, use original query as fallback
                    print(f"[SearchPipeline] Vector DB search strategy detected, using original query for web search")
                    search_queries = [query]  # Use original query for fallback
                    
            except Exception as e:
                print(f"[SearchPipeline] Keyword generation failed: {e}, using original query")
                search_queries = [query]  # Fallback to original query
                
        self.logger.start(f"Keywords: {search_queries}", k, engine_type)
        
        # k is pages per keyword, calculate total target pages
        k_pages_per_keyword = k
        
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
                if result['url'] not in seen_urls and added_from_this_keyword < k_pages_per_keyword:
                    seen_urls.add(result['url'])
                    balanced_results.append(result)
                    added_from_this_keyword += 1
        
        # Process balanced pages with detailed logging
        tasks = []
        process_count = len(balanced_results)
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
        external_keywords: list[str] = None
    ) -> list[ProcessedResult]:
        # k is pages per keyword
        # Let _call handle the calculation after keyword generation
        return await self._call(
            query=query,
            k=k,  # Pages per keyword
            search_k=max(k, 10),  # Results per keyword from API
            in_domain=in_domain,
            engine_type=engine_type,
            include_pdf=include_pdf,
            include_image=include_image,
            external_keywords=external_keywords
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