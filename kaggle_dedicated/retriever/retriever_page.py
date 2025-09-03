from dataclasses import asdict
import math

from .utils import MergeNeighbor, MergeTable, CmdLogger
from .components import *
from .config import *

class DataRetrieverPage:
    """
    Has two phases:\n
    Phase 1: Take web query and download, process page. Result is `WebSource`.\n
    Phase 2: Use retriever to get relavent documents. Result is `RagSource`.\n
    This version retrive on each page, based on relevant score by reranker.
    """
    def __init__(
        self,
        search_config: WebsearchConfig | None = None,
        page_rerank_config: PageRankerConfig | None = None,
        chunk_rerank_config: ChunkRankerConfig | None = None,
        splitter_config: SplitterConfig | None = None,
        rag_config: RagConfig | None = None,
        merge_table_config: MergeTableConfig | None = None,
        merge_neighbor_config: MergeNeighborConfig | None = None
    ) -> None:
        self.logger = CmdLogger("Retriever")
        self.search_pipeline = SearchPipeline(**asdict(search_config or WebsearchConfig()))
        self.converter_1 = WebsearchToWebSourceConverter()
        self.converter_2 = WebSourceToDocumentConverter()
        self.converter_3 = DocumentToRagSourceConverter()
        self.reranker = ReRanker(page_rerank_config or PageRankerConfig(), chunk_rerank_config or ChunkRankerConfig())
        self.splitter = Splitter(splitter_config or SplitterConfig())
        self.rag_retriever = FaissRetriever(rag_config or RagConfig())
        self.tabler_merger = MergeTable(merge_table_config or MergeTableConfig())
        self.neighbor_merger = MergeNeighbor(merge_neighbor_config or MergeNeighborConfig())
    def __del__(self):
        """Todo: Delete embedding"""
        del self.splitter
    async def start(self):
        await self.search_pipeline.start()
    async def websearch(
        self,
        web_query: str,
        k_pages,
        domain_restrict: bool,
        engine: Literal["google", "brave"] = "brave",
        include_pdf: bool = True,
        include_image: bool = True  
    ) -> list[WebSource]:
        """Use web_query to search then return list of `WebSource`."""
        self.logger.start()
        search_results = await self.search_pipeline.call_fast(web_query, k_pages, domain_restrict, engine, include_pdf, include_image)
        self.logger.end("Websearch")
        web_sources = [self.converter_1(search_result) for search_result in search_results]
        return web_sources
    async def rag_retrieve(
        self,
        web_sources: list[WebSource],
        rerank_query: str,
        rag_query: str,
        k_docs: int,
        rerank_chunk: bool = False,
        merge_table: bool = True,
        merge_neighbor: bool = False
    ) -> list[RagSource]:
        """User `web_sources` and `rag_query` to get relavent text, return list of `RagSource`."""
        webpage_docs = [self.converter_2(index, web_source) for index, web_source in enumerate(web_sources)]
        self.logger.start()
        webpage_docs = await self.reranker.rerank_pages(webpage_docs, rerank_query)
        webpage_docs = sorted(webpage_docs, key=lambda doc: doc.metadata["page_index"])
        self.logger.end("Rerank page")
        self.logger.start()
        page_chunks = [self.splitter([webpage_doc]) for webpage_doc in webpage_docs]
        self.logger.end("Split")
        self.logger.start()
        confidences = [float(doc.metadata["confidence"]) for doc in webpage_docs]
        total_confidences = sum(confidences)
        page_k_docs = [math.ceil(confidence/total_confidences*k_docs) for confidence in confidences]
        page_relevant_chunks = [self.rag_retriever(page_chunk, rag_query, k) for page_chunk, k in zip(page_chunks, page_k_docs)]
        self.logger.end("Retrieve")
        if rerank_chunk:
            self.logger.start()
            page_relevant_chunks = [self.reranker.rerank_chunks(relevant_chunk, rerank_query) for relevant_chunk in page_relevant_chunks]
            self.logger.end("Rerank chunk")
        rag_docs = page_relevant_chunks
        if merge_table:
            self.logger.start()
            rag_docs = [self.tabler_merger(page_chunk, rag_doc) for page_chunk, rag_doc in zip(page_chunks, rag_docs)]
            self.logger.end("Merge table")
        if merge_neighbor:
            self.logger.start()
            rag_docs = [self.neighbor_merger(page_chunk, rag_doc) for page_chunk, rag_doc in zip(page_chunks, rag_docs)]
            self.logger.end("Merge neighbor")
        result_docs = []
        for rag_doc in rag_docs:
            result_docs.extend(rag_doc)
        rag_sources: list[RagSource] = self.converter_3(result_docs)
        return rag_sources