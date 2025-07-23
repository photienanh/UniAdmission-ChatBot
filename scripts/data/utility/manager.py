import asyncio
from typing import NamedTuple, Callable, Awaitable, Any
import threading

class ProcessedResult(NamedTuple):
    index: int
    url: str
    text: str
class ProcessInput(NamedTuple):
    index: int
    url: str
    text: str
class ILogger:
    async def success(self, tid: int, offset: int, result: ProcessedResult):
        raise NotImplementedError()
    async def error(self, tid: int, id: str | int, message: Exception):
        raise NotImplementedError()
class IProcessor:
    def process(self, data: ProcessInput) -> ProcessedResult:
        raise NotImplementedError()
class IProvider:
    async def provide(self, index: int, id: str | int) -> ProcessInput:
        raise NotImplementedError()
class IConsumer:
    async def consume(self, id: str | int, data: ProcessedResult):
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
        provider_factory: Callable[[int], IProvider],
        consumer_factory: Callable[[int], IConsumer],
        processor_factory: Callable[[int], IProcessor],
        logger_factory: Callable[[int], ILogger]
    ):
        self.num_workers = num_workers
        def thread_task(tid: int, offset: int, ids: list[str | int]):
            t_provider = provider_factory(tid)
            t_consumer = consumer_factory(tid)
            t_logger = logger_factory(tid)
            t_semaphore = asyncio.Semaphore(concurrent_per_worker)
            t_processor = processor_factory(tid)
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)
            thread_index_count = 0
            async def thread_main():
                async def task(id: str | int):
                    nonlocal thread_index_count
                    async with t_semaphore:
                        try:
                            thread_index_count += 1
                            data = await t_provider.provide(offset+thread_index_count, id)
                            data = t_processor.process(data)
                            await t_consumer.consume(id, data)
                            await t_logger.success(tid, offset, data)
                        except Exception as e:
                            await t_logger.error(tid, id, e)
                jobs = [task(id) for id in ids]
                await asyncio.gather(*jobs)
            event_loop.run_until_complete(thread_main())
            event_loop.close()
        self.threads: list[threading.Thread] = []
        thread_jobs = split(ids, self.num_workers)
        for tid in range(self.num_workers):
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