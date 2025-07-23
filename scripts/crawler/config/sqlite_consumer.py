import asyncio
import queue
from concurrent.futures import ThreadPoolExecutor

from .common import *
try:
    from utility.sqlite_push import PerformanceSQLite
except ImportError:
    from ..utility.sqlite_push import PerformanceSQLite

class SQLiteConsumer(IConsumer):
    def __init__(self, school_id: int, file_path: str, executor: ThreadPoolExecutor):
        self._queue = queue.SimpleQueue()
        self.semaphore = asyncio.Semaphore()
        self.school_id = school_id
        self.handler = PerformanceSQLite(file_path, auto_start=False)
        self.executor = executor
        future = self.executor.submit(self.handler.setup)
        future.result()
    async def consume(self, data: CrawlerResult):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor, 
            self.handler.add_html,
            self.school_id, data.url, data.doc_index, data.html
        )