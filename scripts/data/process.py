import os
from utility import parse_text
import asyncio
import aiofiles
from typing import NamedTuple, Callable, Awaitable, Any
import threading
import time
import math
from typing import Literal

class ProcessedResult(NamedTuple):
    index: int
    url: str
    text: str
class ProcessInput(NamedTuple):
    index: int
    url: str
    text: str
class ILogger:
    async def success(self, tid: int, result: ProcessedResult):
        raise NotImplementedError()
    async def error(self, tid: int, id: str | int, message: Exception):
        raise NotImplementedError()
class IProcessor:
    def process(self, data: ProcessInput) -> ProcessedResult:
        raise NotImplementedError()
def split(lst: list[Any], n: int):
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m) : (i+1)*k + min(i+1, m)] for i in range(n)]
class ProcessingManager:
    def __init__(
        self,
        num_workers: int,
        concurrent_per_worker: int,
        ids: list[str | int],
        provider: Callable[[int, str | int], Awaitable[ProcessInput]],
        consumer: Callable[[ProcessedResult], Awaitable[None]],
        processor_factory: Callable[[], IProcessor],
        logger: ILogger
    ):
        self.num_worers = num_workers
        def thread_task(tid: int, offset: int, ids: list[str | int]):
            t_provider = provider
            t_consumer = consumer
            t_logger = logger
            t_semaphore = asyncio.Semaphore(concurrent_per_worker)
            t_processor = processor_factory()
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)
            count = 0
            async def thread_main():
                async def task(id: str | int):
                    async with t_semaphore:
                        try:
                            data = await t_provider(offset+count, id)
                            data = t_processor.process(data)
                            await t_consumer(data)
                            await t_logger.success(tid, data)
                        except Exception as e:
                            await t_logger.error(tid, id, e)
                jobs = [task(id) for id in ids]
                await asyncio.gather(*jobs)
            asyncio.run(thread_main())
        self.threads: list[threading.Thread] = []
        thread_jobs = split(ids, self.num_worers)
        for tid in range(self.num_worers):
            offset = 0
            for i in range(tid):
                offset += len(thread_jobs[i])
            thread = threading.Thread(target=thread_task, args=[tid, offset, thread_jobs[tid]])
            self.threads.append(thread)
    def run(self):
        for thread in self.threads:
            thread.start()
        for thread in self.threads:
            thread.join()