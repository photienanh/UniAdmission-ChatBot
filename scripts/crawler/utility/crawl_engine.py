import asyncio
import aiohttp
class CrawlEngine:
    def __init__(self, concurrent_limit: int = 4, timeout: float = 30):
        self.limit = concurrent_limit
        self.semaphore = asyncio.Semaphore(concurrent_limit) # Limiter
        self.timeout = timeout
    async def start(self):
        timeout = aiohttp.ClientTimeout(self.timeout)
        connector = aiohttp.TCPConnector(ssl=False)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
    async def get_page(self, url: str) -> str | Exception: 
        async with self.semaphore:
            try:
                async with self.session.get(url) as respone:
                    try:
                        data = await respone.text()
                    except Exception as e:
                        data = e
            except Exception as e:
                data = e
            return data
    def get_task(self, url: str) -> asyncio.Task:
        return asyncio.create_task(self.get_page(url))
    async def stop(self):
        await self.session.close()
        