from .common import IConsumer, ProcessedResult
import aiofiles
import os
import concurrent
import concurrent.futures
import asyncio
from .sqlite_utility import PerformanceSQLite

class SQLiteConsumer(IConsumer):
    def __init__(self, input_path: str, executor: concurrent.futures.ThreadPoolExecutor, min_threshold: int = 2000) -> None:
        self.min_threshold = min_threshold
        self.executor = executor
        self.handler = PerformanceSQLite(input_path, auto_start=False)
        self.executor = executor
        future = self.executor.submit(self.handler.setup)
        future.result()
    async def consume(self, id: int, data: ProcessedResult):
        text = ""
        if len(data.text) < self.min_threshold: 
            text = data.text
        loop = asyncio.get_event_loop()
        # print(id)
        await loop.run_in_executor(
            self.executor,
            self.handler.add_text,
            id, "", text
        )
