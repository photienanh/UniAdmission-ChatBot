from typing import Optional
from .priority_queue import UrlItem

class ILogger:
    def __init__(self):
        pass
    async def error(self, item: UrlItem, error: Exception):
        raise NotImplementedError()
    async def success(self, item: UrlItem):
        raise NotImplementedError()
    async def travel(self, url: str, item: Optional[UrlItem]):
        raise NotImplementedError()
    
