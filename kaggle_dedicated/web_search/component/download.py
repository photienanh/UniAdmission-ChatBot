import aiohttp
import os
import asyncio

from ..schema import SearchResult, HtmlResult
class PageDowloader:
    def __init__(self, session: aiohttp.ClientSession, timeout: float) -> None:
        self.timeout = aiohttp.ClientTimeout(timeout)
        self.session = session
    async def __call__(self, input: SearchResult) -> HtmlResult | None:
        ssl = os.getenv("WEB_SEARCH_SSL", "True").lower() in ("true", "1")
        try:
            async with self.session.get(url=input["url"], timeout=self.timeout, ssl=ssl) as response:
                if response.ok:
                    text = await response.text()
                    result: HtmlResult = {
                        **input,
                        "html": text
                    }
                    return result
                else:
                    print(f"[Page download] Error {response.status}: {await response.text()}")
        except asyncio.TimeoutError:
            print(f"[Page downloader] Timeout: {input['url']}")
        except Exception as e:
            print(f"[Page downloader] Error: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
        return None