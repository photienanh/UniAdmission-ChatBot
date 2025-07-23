from .common import ILogger, ProcessedResult
import time

class CmdLogger(ILogger):
    def __init__(self) -> None:
        super().__init__()
        self.start_time = time.time()
    async def success(self, tid: int, offset: int, result: ProcessedResult):
        index = result.index - offset
        if index % 100 == 0 and index != 0:
            end_time = time.time()
            speed = (index)/(end_time-self.start_time)
            print(f"Completed {tid}:{index} | Speed {speed:.4f} items/s")
    async def error(self, tid: int, id: str | int, message: Exception):
        print(f"Error: {tid} | {id} | {message}")