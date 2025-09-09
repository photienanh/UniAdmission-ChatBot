import aiohttp
import os
import asyncio
from typing import Awaitable, TYPE_CHECKING

if TYPE_CHECKING:
    CoroutineType = asyncio._CoroutineLike
else:
    CoroutineType = Awaitable

from ..schema import SearchResult, HtmlResult
class PageDowloader:
    def __init__(self, session: aiohttp.ClientSession, concurrent_page_download: int, timeout: float) -> None:
        self.timeout = aiohttp.ClientTimeout(timeout)
        self.session = session
        self.semaphore = asyncio.Semaphore(concurrent_page_download)
        self._page_download_limit = concurrent_page_download
    async def _run_jobs(self, jobs: list[CoroutineType], k_pages: int):
        """
        This function attempt to run jobs.\n
        It would stop when reach k_pages, and keep input order.\n
        Only get result of next task when previous task is completed.
        """
        print(f"[Page download] Attempt to download {k_pages} pages from {len(jobs)} urls")
        tasks = [asyncio.create_task(job) for job in jobs]
        page_count = 0
        results: list[None | HtmlResult] = [None] * len(jobs)
        for index, task in enumerate(tasks):
            try:
                result = await task
            except asyncio.CancelledError:
                result = None
            results.append(result)
            if result is not None:
                page_count += 1
                if page_count >= k_pages:
                    for task in tasks[index+1:]:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    break
        return results
    async def _null_task(self):
        return None
    async def download(self, search_results: list[SearchResult], k_pages: int, include_pdf: bool, include_image: bool) -> list[HtmlResult]:
        """Download up to k_pages from input list"""
        ssl = os.getenv("WEB_SEARCH_SSL", "True").lower() in ("true", "1")
        jobs = []
        for search_result in search_results:
            if search_result["url"].endswith(".pdf"):
                if include_pdf:
                    jobs.append(self._handle_file_task(search_result))
                else:
                    jobs.append(self._null_task())
            else:
                jobs.append(self._download_task(ssl, search_result))
        job_results =  await self._run_jobs(jobs, k_pages)
        html_results: list[HtmlResult] = []
        for job_result in job_results:
            if job_result:
                html_results.append(job_result)
        print(f"[Page download] Success download {len(html_results)} pages")
        return html_results
    async def _handle_file_task(self, search_result: SearchResult) -> HtmlResult | None:
        # Async only to make compatible
        if search_result["url"].endswith(".pdf"):
            result: HtmlResult = {
                **search_result,
                "html": f'[{search_result["title"]}]({search_result["url"]})'
            }
            return result
    async def _download_task(self, ssl: bool, search_result: SearchResult) -> HtmlResult | None:
        async with self.semaphore:
            try:
                async with self.session.get(url=search_result["url"], timeout=self.timeout, ssl=ssl) as response:
                    if response.ok:
                        text = await response.text()
                        result: HtmlResult = {
                            **search_result,
                            "html": text
                        }
                        return result
                    else:
                        print(f"[Page download] Error {response.status}")#: {await response.text()}")
            except asyncio.TimeoutError:
                print(f"[Page downloader] Timeout: {search_result['url']}")
            except Exception as e:
                print(f"[Page downloader] Error: {str(e)[:100]}")
                # import traceback
                # traceback.print_exc()
            return None