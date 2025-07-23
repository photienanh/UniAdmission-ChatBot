import pickle
import asyncio
import pickle
from typing import NamedTuple, Callable, Awaitable

# Absolute import
from utility import (
    CrawlEngine, UrlPriorityQueue, UrlItem, UrlKey,
    extract_anchor_data, url_reconstructor
)
try:
    from format import GeneralInfo
except:
    from ..format import GeneralInfo
    
class CrawlerResult(NamedTuple):
    doc_index: int
    url: str
    html: str

class ILogger:
    def __init__(self):
        pass
    async def error(self, item: UrlItem, error: Exception):
        raise NotImplementedError()
    async def success(self, item: UrlItem):
        raise NotImplementedError()
    async def travel_valid(self, item: UrlItem):
        raise NotImplementedError()
    async def travel_invalid(self, from_url: str, url: str, travel_index: int):
        raise NotImplementedError()
class IConsumer:
    def __init__(self) -> None:
        pass
    async def consume(self, result: CrawlerResult):
        raise NotImplementedError()
    
    

class SchoolCrawler:
    def __init__(self, 
            info: GeneralInfo,
            pq: UrlPriorityQueue,
            logger: ILogger,
            consumer: IConsumer,
            page_limit: int = 500,
            concurrent_limit: int = 4,
            max_retry: int = 3,
            timeout: float = 30,
        ):
        self.consumer = consumer
        self.logger = logger
        self.pq = pq
        self.info = info
        self.engine = CrawlEngine(concurrent_limit, timeout)
        self.success_count = 0
        self.page_limit = page_limit
        self.max_rety = max_retry
        self.failed_count = 0

    async def run(self):
        await self.engine.start()
        item = UrlItem(
            UrlKey(0, 0, 0, 0),
            "",
            self.info["Website"],
            ""
        ) # For log first travel only
        self.pq.add(0, item.from_url, item.url, item.html)
        await self.logger.travel_valid(item)
        # try
        while len(self.pq) > 0:
            batch_items: list[UrlItem] = []
            batch_jobs = []
            batch_success_count = 0
            for _ in range(self.engine.limit):
                if len(self.pq) > 0:
                    (priority, item) = self.pq.pop()
                    batch_items.append(item)
                    job = self.engine.get_task(item.url)
                    batch_jobs.append(job)
                    # print(f"Start {n_priority} {item.url}")
            htmls = await asyncio.gather(*batch_jobs)
            for index, html in enumerate(htmls):
                item = batch_items[index]
                if isinstance(html, Exception):
                    self.failed_count += 1
                    await self.logger.error(item, html)
                    if item.key.retry < self.max_rety:
                        self.pq.retry(item)
                else:
                    batch_success_count += 1
                    anchor_data = extract_anchor_data(html)
                    result = CrawlerResult(
                        doc_index=self.success_count+batch_success_count,
                        url=item.url,
                        
                        html=html
                    )
                    await self.consumer.consume(result)
                    await self.logger.success(item)
                    for anchor_item in anchor_data:
                        new_url = url_reconstructor(item.url, anchor_item.href)
                        new_item = self.pq.add(item.key.level+1, item.url, new_url, anchor_item.text)
                        if new_item != None:
                            await self.logger.travel_valid(new_item)
                        else:
                            await self.logger.travel_invalid(item.url, new_url, item.key.index)
            self.success_count += batch_success_count
            if self.success_count >= self.page_limit:
                break
            else:
                # print(self.count,  len(self.url_queue))
                pass
        await self.engine.stop()