import concurrent
import concurrent.futures
import asyncio
import datetime

from .common import *
try:
    from utility.sqlite_push import PerformanceSQLite
except ImportError:
    from ..utility.sqlite_push import PerformanceSQLite

class SQLiteLogger(ILogger):
    def __init__(self, school_id: int, file_path: str, executor: concurrent.futures.Executor):
        self.school_id = school_id
        self.handler = PerformanceSQLite(file_path)
        self.executor = executor
        future = self.executor.submit(self.handler.setup)
        future.result()
    async def success(self, item: UrlItem):
        pass
    async def error(self, item: UrlItem, error: Exception):
        time = datetime.datetime.today().strftime(f"%d:%m:%Y-%H:%M:%S")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self.handler.add_error_log,
            self.school_id, time, item.key.index, item.key.retry, item.from_url, item.url, str(error)
        )
    async def travel_valid(self, item: UrlItem):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self.handler.add_valid_travel_log,
            self.school_id, item.key.index, item.key.score, item.key.retry, item.from_url, item.url
        )
    async def travel_invalid(self, from_url: str, url: str, travel_index: int):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self.handler.add_invalid_travel_log,
            self.school_id, travel_index, from_url, url
        )
