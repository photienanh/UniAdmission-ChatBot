from .schema import WebSource, RagSource, FileSource, AbstractSearchEngine, SearchResult, HtmlResult
from .search_engines import BraveSearchEngine, GoogleSearchEngine
from .ranker import PageRerankModelProtocol, ChunkRanker
from .downloader import PageDowloader
from .extractor import ContentExtractor
from .retriever import Splitter, FaissRetriever, Merger
from .config import *
from .retriever.utils import CmdLogger
import time
import math
from server import GenerationParams
import asyncio
import aiohttp

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
        
        self.logger = CmdLogger("Retriever")
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
        if len(queries_and_domains) == 0: return [], []
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
        web_sources_list = [await self._process(html_results) for html_results in html_results_list]
        web_sources_list = self._pages_list_reorder(web_sources_list)
        # K-query
        # each query have k-page
        # each page have k-source
        rag_sources_list_list = [
            await self._split_rag_merge(
                item if isinstance(item, str) else item[0],
                web_sources,
                params
            ) for item, web_sources in  zip(queries_and_domains, web_sources_list)
        ]
        
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
        self.logger.start()
        page_score_threshold = params.get("page_score_threshold", 0.51)
        search_results = await self._page_ranker_model.rerank_page(
            pages=search_results,
            query=query,
            relative_threshold=page_score_threshold,
            params=params
        )
        self.logger.end("Rerank")
        return search_results
    async def _download(
        self,
        params: GenerationParams,
        search_results_list: list[list[SearchResult]],
    ) -> list[list[HtmlResult]]:
        """Combined download, to ensure same pages have same contents."""
        filtered_search_results_list: list[list[SearchResult]] = []
        recorded_url = set()
        for search_results in search_results_list:
            filtered_search_results: list[SearchResult] =[]
            for search_result in search_results:
                if search_result["url"] not in recorded_url:
                    recorded_url.add(search_result["url"])
                    filtered_search_results.append(search_result)
            filtered_search_results_list.append(filtered_search_results)
        tasks = []
        k_pages = params.get("k_pages", 3) # Todo: Split by query priority
        include_pdf = params.get("include_pdf", False)
        include_image = params.get("include_image", False)
        async def download_task(search_results: list[SearchResult]) -> list[HtmlResult]:
            return await self._page_downloader.download(search_results, k_pages, include_pdf, include_image)
        for filtered_search_results in filtered_search_results_list:
            tasks.append(asyncio.create_task(download_task(filtered_search_results)))
        html_results_list = await asyncio.gather(*tasks)
        flat_html_results: dict[str, HtmlResult] = {}
        for html_results in html_results_list:
            for htm_result in html_results:
                if htm_result["url"] not in flat_html_results:
                    flat_html_results[htm_result["url"]] = htm_result
        
        final_results_list: list[list[HtmlResult]] = []
        for search_results in search_results_list:
            # print("-----------")
            final_results: list[HtmlResult] = []
            for search_result in search_results:
                if search_result["url"] in flat_html_results:
                    final_results.append(flat_html_results[search_result["url"]])
                    # print(search_result["url"])
                if len(final_results) == k_pages:
                    break
            final_results_list.append(final_results)
        return final_results_list
    async def _process(
        self,
        html_results: list[HtmlResult]
    ) -> list[WebSource]:
        # Process page
        self.logger.start()
        web_sources: list[WebSource] = await self._page_extractor.extract(html_results)
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
        merge_table = params.get("merge_table", False)
        merge_neighbor = params.get("merge_neighbor", False)
        chunk_score_threshold = params.get("chunk_score_threshold", 0.5)
        k_docs = params.get("k_docs", 5) # Todo: Split by query priority
        
        rag_sources_list: list[list[RagSource]] = []
        scores = [source["score"] for source in web_sources]
        total_scores = sum(scores) 
        if total_scores == 0: # When reranker fail
            page_k_docs = [math.ceil(k_docs/len(scores)) for _ in scores]
        else:
            page_k_docs = [math.ceil(confidence/total_scores*k_docs) for confidence in scores]
        for web_source, page_k_doc in zip(web_sources, page_k_docs):
            rag_sources = self._splitter.split(web_source)
            relavent_sources = self._rag.retrieve(rag_sources, query, page_k_doc)
            rag_sources = self._merger.merge(rag_sources, relavent_sources, merge_table, merge_neighbor)
            rag_sources = self._chunk_ranker.rerank_chunks(relavent_sources, query, chunk_score_threshold)
            rag_sources_list.append(rag_sources)
        self.logger.end("RAG")
        return rag_sources_list
    async def _merge_rag_source(
        self,
        rag_sources_list_list: list[list[list[RagSource]]]
    ) -> list[RagSource]:
        """Combine all ragsource, remove duplicate chunks"""
        import json
        with open("FUC.json", 'w', encoding='utf-8') as file:
            file.write(json.dumps(rag_sources_list_list, ensure_ascii=False))
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
        self.logger.start()
        page_score_threshold = params.get("page_score_threshold", 0.5)
        search_results = await self._page_ranker_model.rerank_page(
            pages=search_results,
            query=query,
            relative_threshold=page_score_threshold,
            params=params
        )
        self.logger.end("Rerank")
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
        web_sources: list[WebSource] = await self._page_extractor.extract(html_results)
        self.logger.end("Process")
        # Split, rag, merge
        self.logger.start()
        merge_table = params.get("merge_table", True)
        merge_neighbor = params.get("merge_neighbor", True)
        chunk_score_threshold = params.get("chunk_score_threshold", 0.5)
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
            rag_sources = self._chunk_ranker.rerank_chunks(relavent_sources, query, chunk_score_threshold)
        
        self.logger.end("RAG")
        return web_sources, rag_sources 