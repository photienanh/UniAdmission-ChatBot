from .schema import WebSource, RagSource, FileSource, AbstractSearchEngine, SearchResult, HtmlResult
from .search_engines import BraveSearchEngine, GoogleSearchEngine
from .ranker import PageRerankModelProtocol, ChunkRanker
from .downloader import PageDowloader
from .extractor import ContentExtractor
from .retriever import Splitter, FaissRetriever, Merger
from .config import *
from .retriever.utils import CmdLogger
from .snippet_checker import HeuristicSnippetChecker, SnippetCheckerProtocol
import time
import math
from server import GenerationParams
import asyncio
import aiohttp
from typing import cast

class DataRetrieverPipeline:
    def __init__(
        self, 
        page_ranker_model: PageRerankModelProtocol, 
        concurrent_config: DataRetrieverConcurrentConig | None = None, 
        websearch_config: WebsearchConfig | None = None,
        splitter_config: SplitterConfig | None = None,
        rag_config: RagConfig | None = None,
        table_merge_config: MergeTableConfig | None = None,
        neighbor_merge_config: MergeNeighborConfig | None = None,
        chunk_ranker_config: ChunkRankerConfig | None = None
    ) -> None:
        # Config
        self._concurrent_config = concurrent_config or DataRetrieverConcurrentConig()
        self._query_semaphore = asyncio.Semaphore(self._concurrent_config.engine_query_limit)
        
        # Websearch
        self._websearch_config = websearch_config or WebsearchConfig()
        self._brave_search_engine: AbstractSearchEngine = BraveSearchEngine()
        self._google_search_engine: AbstractSearchEngine = GoogleSearchEngine()
        
        # Page ranker
        self._page_ranker_model = page_ranker_model

        # Splitter
        self._splitter = Splitter(splitter_config or SplitterConfig())
        self._rag = FaissRetriever(rag_config or RagConfig())
        self._merger = Merger(
            neighbor_merge_config or MergeNeighborConfig(),
            table_merge_config or MergeTableConfig()
        )
        
        # Chunk ranker
        self._chunk_ranker = ChunkRanker(chunk_ranker_config or ChunkRankerConfig())
        
        # Snippet checker - kiểm tra snippet có đủ thông tin không
        self._snippet_checker: SnippetCheckerProtocol = HeuristicSnippetChecker(
            min_snippet_length=150,
            min_keyword_match_ratio=0.4
        )
        
        self.logger = CmdLogger("Retriever")
    
    def _preview_text(self, text: str, limit: int = 200) -> str:
        text = text.replace("\n", " ").strip()
        if len(text) <= limit:
            return text
        return text[:limit] + "..."
    
    def _log_chunks(self, prefix: str, title: str, chunks: list[RagSource], max_samples: int = 3):
        if not chunks:
            self.logger.log(f"{prefix} {title}: no chunks")
            return
        self.logger.log(f"{prefix} {title}: total {len(chunks)} chunks")
        for chunk in chunks[:max_samples]:
            preview = self._preview_text(chunk.get("text", ""))
            self.logger.log(f"{prefix} chunk#{chunk.get('chunk_index', 0)}: {preview}")
        if len(chunks) > max_samples:
            self.logger.log(f"{prefix} ... (+{len(chunks) - max_samples} more)")
    
    def _prioritize_table_chunks(
        self,
        total_sources: list[RagSource],
        retrieved_sources: list[RagSource],
        max_additional: int = 3
    ) -> list[RagSource]:
        """Ensure chunks that contain tables are always included"""
        table_chunks: list[RagSource] = []
        existing_indexes = {source["chunk_index"] for source in retrieved_sources}
        for source in total_sources:
            text = source.get("text", "")
            if "[BẢNG]" in text or text.count("|") >= 3:
                if source["chunk_index"] not in existing_indexes:
                    table_chunks.append(source)
            if len(table_chunks) >= max_additional:
                break
        if table_chunks:
            self.logger.log(f"[Prioritize] Added {len(table_chunks)} table chunks before retrieval output")
        return table_chunks + retrieved_sources
    
    async def start(self):
        self._aio_session = aiohttp.ClientSession()
        # Page downloader
        self._page_downloader = PageDowloader(self._aio_session, self._concurrent_config.page_download_limit, self._websearch_config.page_timeout)
        # Page extractor
        self._page_extractor = ContentExtractor(self._aio_session, self._concurrent_config.file_download_limit, self._websearch_config.file_timeout, self._websearch_config.max_file_per_page)
    async def stop(self):
        await self._aio_session.close()
    async def retrieve_sep(
        self,
        params: GenerationParams,
        queries_and_domains: list[str | tuple[str, list[str]]]
    ) -> tuple[list[WebSource], list[RagSource]]:
        if len(queries_and_domains) == 0: return [], []
        tasks = []
        async def task(query: str, school_domains: list[str]):
            async with self._query_semaphore:
                return await self.retrieve_single_page(params, query, school_domains)
        for item in queries_and_domains: #type:ignore
            if isinstance(item, str):
                # Only query, no shool domain
                tasks.append(asyncio.create_task(task(item, [])))
            else:
                tasks.append(asyncio.create_task(task(item[0], item[1])))
        results = await asyncio.gather(*tasks)
        web_sources: list[WebSource] = []
        rag_sources: list[RagSource] = []
        for item in results:
            web_sources.extend(item[0])
            rag_sources.extend(item[1])
        return web_sources, rag_sources
    async def retrieve(
        self,
        params: GenerationParams,
        queries_and_domains: list[str | tuple[str, list[str]]]
    ) -> tuple[list[WebSource], list[RagSource]]:
        query_count = len(queries_and_domains)
        if query_count == 0:
            return [], []

        include_pdf = params.get("include_pdf", False)
        # Clone params to avoid mutating caller reference
        params = cast(GenerationParams, {**params})
        if "llm_rerank" not in params:
            params["llm_rerank"] = query_count > 1
            mode = "ON" if params["llm_rerank"] else "OFF"
            self.logger.log(
                f"Auto llm_rerank={mode} (query_count={query_count})"
            )
        else:
            mode = "ON" if params["llm_rerank"] else "OFF"
            self.logger.log(
                f"Manual llm_rerank={mode} (query_count={query_count})"
            )
        if "chunk_rerank" not in params:
            params["chunk_rerank"] = query_count > 1
            mode = "ON" if params["chunk_rerank"] else "OFF"
            self.logger.log(
                f"Auto chunk_rerank={mode} (query_count={query_count})"
            )
        else:
            mode = "ON" if params["chunk_rerank"] else "OFF"
            self.logger.log(
                f"Manual chunk_rerank={mode} (query_count={query_count})"
            )

        tasks = []
        async def search_and_rerank_task(query: str, school_domains: list[str]):
            async with self._query_semaphore:
                return await self._search_and_rerank(params, query, school_domains)
        for item in queries_and_domains: #type:ignore
            if isinstance(item, str):
                # Only query, no shool domain
                tasks.append(asyncio.create_task(search_and_rerank_task(item, [])))
            else:
                tasks.append(asyncio.create_task(search_and_rerank_task(item[0], item[1])))
                
        search_results_list: list[list[SearchResult]] = await asyncio.gather(*tasks)
        html_results_list = await self._download(params, search_results_list)
        
        # PARALLEL: Process và RAG chạy song song cho các queries khác nhau
        # Tạo tasks cho process và RAG
        async def process_and_rag_task(
            html_results: list[HtmlResult], 
            query: str, 
            include_pdf: bool
        ) -> tuple[list[WebSource], list[list[RagSource]]]:
            # Process pages
            web_sources = await self._process(html_results, include_pdf)
            # RAG processing
            rag_sources_list = await self._split_rag_merge(query, web_sources, params)
            return web_sources, rag_sources_list
        
        # Chạy process và RAG song song cho tất cả queries
        process_rag_tasks = [
            asyncio.create_task(
                process_and_rag_task(
                    html_results,
                    item if isinstance(item, str) else item[0],
                    include_pdf
                )
            )
            for item, html_results in zip(queries_and_domains, html_results_list)
        ]
        
        process_rag_results = await asyncio.gather(*process_rag_tasks)
        web_sources_list = [result[0] for result in process_rag_results]
        rag_sources_list_list = [result[1] for result in process_rag_results]
        
        web_sources_list = self._pages_list_reorder(web_sources_list)
        
        rag_sources = await self._merge_rag_source(rag_sources_list_list) 
        web_sources = await self._merge_web_sources(web_sources_list)
        return web_sources, rag_sources
    def _pages_list_reorder(
        self,
        web_sources_list: list[list[WebSource]]
    ) -> list[list[WebSource]]:
        web_sources_list = sorted(
            web_sources_list,
            key=lambda web_sources: web_sources[0]["score"] if len(web_sources) > 0 else 0,
            reverse=True
        )
        return web_sources_list
    async def _search_and_rerank(
        self,
        params: GenerationParams,
        query: str,
        school_domains: list[str]
    ) -> list[SearchResult]:
        # Websearch
        self.logger.start()
        engine_type = params.get("engine_type", "brave")
        domain_restrict = params.get("domain_restrict", False)
        time_metric = params.get("time_metric")
        time_range = params.get("time_range")         
        search_results: list[SearchResult] = []
        if engine_type == "brave":
            search_func = self._brave_search_engine.search
        else:
            search_func = self._google_search_engine.search
        search_results = await search_func(
            query=query,
            domain_restrict=domain_restrict,
            school_domains=school_domains,
            time_metric=time_metric,
            time_range=time_range
        )
        self.logger.end("Websearch")
        # Rerank Page
        use_rerank = params.get("llm_rerank", True)
        if use_rerank:
            self.logger.start()
            page_score_threshold = params.get("page_score_threshold", 0.51)
            search_results = await self._page_ranker_model.rerank_page(
                pages=search_results,
                query=query,
                relative_threshold=page_score_threshold,
                params=params
            )
            self.logger.end("Rerank")
        else:
            self.logger.log("Rerank: Skip (llm_rerank=False)")
        return search_results
    async def _download(
        self,
        params: GenerationParams,
        search_results_list: list[list[SearchResult]],
    ) -> list[list[HtmlResult]]:
        """
        Combined download với tối ưu snippet:
        - Kiểm tra snippet có đủ thông tin không
        - Nếu đủ → dùng snippet, không crawl
        - Nếu không đủ → crawl URL
        """
        use_snippet_optimization = params.get("use_snippet_optimization", True)
        k_pages = params.get("k_pages", 3)
        
        filtered_search_results_list: list[list[SearchResult]] = []
        recorded_url = set()
        for search_results in search_results_list:
            filtered_search_results: list[SearchResult] =[]
            for search_result in search_results:
                if search_result["url"] not in recorded_url:
                    recorded_url.add(search_result["url"])
                    filtered_search_results.append(search_result)
            filtered_search_results_list.append(filtered_search_results)
        
        # Bước 1: Kiểm tra snippet và phân loại (PARALLEL)
        snippet_sufficient_results: dict[str, HtmlResult] = {}  # URL -> HtmlResult từ snippet
        need_crawl_results_list: list[list[SearchResult]] = []  # Các URL cần crawl
        
        if use_snippet_optimization:
            self.logger.start()
            
            # Tạo tất cả snippet check tasks song song
            async def check_snippet(search_result: SearchResult) -> tuple[SearchResult, bool]:
                snippet = search_result.get("description", "")
                title = search_result.get("title", "")
                query = search_result.get("query", "")
                url = search_result.get("url", "")
                
                is_sufficient = await self._snippet_checker.is_sufficient(
                    snippet=snippet,
                    title=title,
                    query=query,
                    url=url,
                    params=params
                )
                return search_result, is_sufficient
            
            # Chạy tất cả snippet checks song song
            for search_results in filtered_search_results_list:
                # Tạo tasks cho tất cả search_results trong list này
                check_tasks = [asyncio.create_task(check_snippet(sr)) for sr in search_results]
                check_results = await asyncio.gather(*check_tasks)
                
                need_crawl: list[SearchResult] = []
                for search_result, is_sufficient in check_results:
                    snippet = search_result.get("description", "")
                    title = search_result.get("title", "")
                    url = search_result.get("url", "")
                    
                    if is_sufficient:
                        # Dùng snippet làm html, không cần crawl
                        html_result: HtmlResult = {
                            **search_result,
                            "html": f"{title}\n\n{snippet}",  # Combine title + snippet
                            "score": search_result.get("score", 1.0)
                        }
                        snippet_sufficient_results[search_result["url"]] = html_result
                        snippet_preview = snippet[:150] + "..." if len(snippet) > 150 else snippet
                        print(f"[Snippet] ✓ Đủ thông tin:")
                        print(f"  Title: {title}")
                        print(f"  URL: {url}")
                        print(f"  Snippet: {snippet_preview}")
                    else:
                        # Cần crawl
                        need_crawl.append(search_result)
                        snippet_preview = snippet[:150] + "..." if len(snippet) > 150 else snippet
                        print(f"[Snippet] ✗ Cần crawl:")
                        print(f"  Title: {title}")
                        print(f"  URL: {url}")
                        print(f"  Snippet: {snippet_preview}")
                
                need_crawl_results_list.append(need_crawl)
            self.logger.end("Snippet Check")
        else:
            # Không dùng optimization, crawl tất cả
            need_crawl_results_list = filtered_search_results_list
        
        # Bước 2: Crawl các URL cần thiết (giới hạn k_pages)
        tasks = []
        include_pdf = params.get("include_pdf", False)
        include_image = params.get("include_image", False)
        
        async def download_task(search_results: list[SearchResult]) -> list[HtmlResult]:
            return await self._page_downloader.download(search_results, k_pages, include_pdf, include_image)
        
        # Đo thời gian crawl
        crawl_start_time = time.time()
        total_urls_to_crawl = sum(len(results) for results in need_crawl_results_list)
        
        if total_urls_to_crawl > 0:
            print(f"[Download] Bắt đầu crawl {total_urls_to_crawl} URL(s)...")
        
        for need_crawl_results in need_crawl_results_list:
            if len(need_crawl_results) > 0:
                tasks.append(asyncio.create_task(download_task(need_crawl_results)))
        
        html_results_list = await asyncio.gather(*tasks) if tasks else []
        
        crawl_end_time = time.time()
        crawl_duration = crawl_end_time - crawl_start_time
        
        # Merge kết quả crawl
        flat_html_results: dict[str, HtmlResult] = {}
        for html_results in html_results_list:
            for html_result in html_results:
                if html_result["url"] not in flat_html_results:
                    flat_html_results[html_result["url"]] = html_result
        
        # Merge với snippet results
        flat_html_results.update(snippet_sufficient_results)
        
        # Bước 3: Tạo final results theo thứ tự và giới hạn k_pages
        final_results_list: list[list[HtmlResult]] = []
        for search_results in search_results_list:
            final_results: list[HtmlResult] = []
            for search_result in search_results:
                if search_result["url"] in flat_html_results:
                    final_results.append(flat_html_results[search_result["url"]])
                if len(final_results) >= k_pages:
                    break
            final_results_list.append(final_results)
        
        # Log thống kê
        total_snippet = len(snippet_sufficient_results)
        total_crawled = len([r for r in flat_html_results.values() if r["url"] not in snippet_sufficient_results])
        
        if total_urls_to_crawl > 0:
            avg_time_per_url = crawl_duration / total_urls_to_crawl
            print(f"[Download] Snippet đủ: {total_snippet}, Đã crawl: {total_crawled}")
            print(f"[Download] Thời gian crawl: {crawl_duration:.2f}s (trung bình {avg_time_per_url:.2f}s/URL)")
        else:
            print(f"[Download] Snippet đủ: {total_snippet}, Không cần crawl (0 URL)")
        
        return final_results_list
    async def _process(
        self,
        html_results: list[HtmlResult],
        include_pdf: bool
    ) -> list[WebSource]:
        # Process page
        self.logger.start()
        web_sources: list[WebSource] = await self._page_extractor.extract(html_results, include_pdf)
        self.logger.end("Process")
        return web_sources
    async def _split_rag_merge(
        self,
        query: str,
        web_sources: list[WebSource],
        params: GenerationParams
    ) -> list[list[RagSource]]:
        # Split, rag, merge
        self.logger.start()
        merge_table = params.get("merge_table", True)
        merge_neighbor = params.get("merge_neighbor", True)
        chunk_score_threshold = params.get("chunk_score_threshold", 0.5)
        chunk_rerank_enabled = params.get("chunk_rerank", False)
        k_docs = params.get("k_docs", 5) # Todo: Split by query priority
        
        rag_sources_list: list[list[RagSource]] = []
        scores = [source["score"] for source in web_sources]
        total_scores = sum(scores) 
        if total_scores == 0: # When reranker fail
            page_k_docs = [math.ceil(k_docs/len(scores)) for _ in scores]
        else:
            page_k_docs = [math.ceil(confidence/total_scores*k_docs) for confidence in scores]
        
        # PARALLEL: Xử lý RAG cho các web_sources song song
        # Wrap synchronous functions trong asyncio.to_thread để chạy song song
        async def process_rag_for_source(web_source: WebSource, page_k_doc: int) -> list[RagSource]:
            # Chạy các CPU-bound operations trong thread pool
            rag_sources = await asyncio.to_thread(self._splitter.split, web_source)
            self._log_chunks("[Split]", web_source["title"], rag_sources)
            relavent_sources = await asyncio.to_thread(self._rag.retrieve, rag_sources, query, page_k_doc)
            relavent_sources = self._prioritize_table_chunks(rag_sources, relavent_sources)
            self._log_chunks("[RAG]", web_source["title"], relavent_sources)
            relavent_sources = await asyncio.to_thread(
                self._merger.merge, rag_sources, relavent_sources, merge_table, merge_neighbor
            )
            if relavent_sources:
                self._log_chunks("[Merge]", web_source["title"], relavent_sources)
            if chunk_rerank_enabled:
                relavent_sources = await asyncio.to_thread(
                    self._chunk_ranker.rerank_chunks, relavent_sources, query, chunk_score_threshold
                )
                self._log_chunks("[ChunkRerank]", web_source["title"], relavent_sources)
            return relavent_sources
        
        # Chạy RAG processing song song cho tất cả web_sources
        rag_tasks = [
            asyncio.create_task(process_rag_for_source(web_source, page_k_doc))
            for web_source, page_k_doc in zip(web_sources, page_k_docs)
        ]
        rag_sources_list = await asyncio.gather(*rag_tasks)
        
        self.logger.end("RAG")
        return rag_sources_list
    async def _merge_rag_source(
        self,
        rag_sources_list_list: list[list[list[RagSource]]]
    ) -> list[RagSource]:
        """Combine all ragsource, remove duplicate chunks"""
        import json
        # with open("log.json", 'w', encoding='utf-8') as file:
        #     file.write(json.dumps(rag_sources_list_list, ensure_ascii=False))
        url_indexes: dict[str, set[int]] = {}
        final_rag_sources: list[RagSource] = []
        for rag_sources_list in rag_sources_list_list:
            for rag_sources in rag_sources_list:
                for rag_source in rag_sources:
                    chunk_index = rag_source["chunk_index"]
                    if rag_source["url"] not in url_indexes:
                        print(rag_source["url"])
                        url_indexes[rag_source["url"]] = set([chunk_index])
                        final_rag_sources.append(rag_source)
                    else:
                        indexes = url_indexes[rag_source["url"]]
                        if chunk_index not in indexes:
                            indexes.add(chunk_index)
                            final_rag_sources.append(rag_source)
        return final_rag_sources
    async def _merge_web_sources(
        self,
        web_sources_list: list[list[WebSource]]
    ) -> list[WebSource]:
        urls = set()
        final_web_sources: list[WebSource] = []
        for web_sources in web_sources_list:
            for web_source in web_sources:
                if web_source["url"] not in urls:
                    urls.add(web_source["url"])
                    final_web_sources.append(web_source)
        return final_web_sources
    async def retrieve_single_page(
        self,
        params: GenerationParams,
        query: str,
        school_domains: list[str]
    ) -> tuple[list[WebSource], list[RagSource]]:
        # Websearch
        self.logger.start()
        engine_type = params.get("engine_type", "brave")
        domain_restrict = params.get("domain_restrict", False)
        time_metric = params.get("time_metric")
        time_range = params.get("time_range")         
        search_results: list[SearchResult] = []
        if engine_type == "brave":
            search_func = self._brave_search_engine.search
        else:
            search_func = self._google_search_engine.search
        search_results = await search_func(
            query=query,
            domain_restrict=domain_restrict,
            school_domains=school_domains,
            time_metric=time_metric,
            time_range=time_range
        )
        self.logger.end("Websearch")
        # Rerank Page
        use_rerank = params.get("llm_rerank", True)
        if use_rerank:
            self.logger.start()
            page_score_threshold = params.get("page_score_threshold", 0.5)
            search_results = await self._page_ranker_model.rerank_page(
                pages=search_results,
                query=query,
                relative_threshold=page_score_threshold,
                params=params
            )
            self.logger.end("Rerank")
        else:
            self.logger.log("Rerank: Skip (llm_rerank=False)")
        # Download page
        self.logger.start()
        k_pages = params.get("k_pages", 3) # Todo: Split by query priority
        include_pdf = params.get("include_pdf", False)
        include_image = params.get("include_image", False)
        html_results: list[HtmlResult] = await self._page_downloader.download(
            search_results, 
            k_pages, 
            include_pdf, 
            include_image
        )
        self.logger.end("Download")
        # Process page
        self.logger.start()
        web_sources: list[WebSource] = await self._page_extractor.extract(html_results, include_pdf)
        self.logger.end("Process")
        # Split, rag, merge
        self.logger.start()
        merge_table = params.get("merge_table", True)
        merge_neighbor = params.get("merge_neighbor", True)
        chunk_score_threshold = params.get("chunk_score_threshold", 0.5)
        chunk_rerank_enabled = params.get("chunk_rerank", False)
        k_docs = params.get("k_docs", 5) # Todo: Split by query priority
        
        rag_sources: list[RagSource] = []
        scores = [source["score"] for source in web_sources]
        total_scores = sum(scores) 
        if total_scores == 0: # When reranker fail
            page_k_docs = [math.ceil(k_docs/len(scores)) for _ in scores]
        else:
            page_k_docs = [math.ceil(confidence/total_scores*k_docs) for confidence in scores]
        for web_source, page_k_doc in zip(web_sources, page_k_docs):
            rag_sources = self._splitter.split(web_source)
            relavent_sources = self._rag.retrieve(rag_sources, query, page_k_doc)
            relavent_sources = self._merger.merge(rag_sources, relavent_sources, merge_table, merge_neighbor)
            if chunk_rerank_enabled:
                relavent_sources = self._chunk_ranker.rerank_chunks(relavent_sources, query, chunk_score_threshold)
            rag_sources = relavent_sources
        
        self.logger.end("RAG")
        return web_sources, rag_sources 