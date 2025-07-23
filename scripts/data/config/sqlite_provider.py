from .common import IProvider, ProcessInput
import aiofiles
import re
import os
import concurrent
import concurrent.futures
import asyncio
from .sqlite_utility import PerformanceSQLite

URL_PATTERN = re.compile(r'<!--\sSource:(.*?)\s-->')
class SQLiteProvider(IProvider):
    def __init__(self, input_path: str, executor: concurrent.futures.ThreadPoolExecutor) -> None:
        self.handler = PerformanceSQLite(input_path, auto_start=False)
        self.executor = executor
        future = self.executor.submit(self.handler.setup)
        future.result()
    async def provide(self, index: int, id: int) -> ProcessInput:
        loop = asyncio.get_event_loop()
        (url, title, html) = await loop.run_in_executor(
            self.executor,
            self.handler.retrieve_html,
            id
        )
        return ProcessInput(index, url, html)
    