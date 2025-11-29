import aiohttp
import os
import asyncio
import random
from typing import Awaitable, TYPE_CHECKING, Optional

from bs4 import BeautifulSoup, Comment

if TYPE_CHECKING:
    CoroutineType = asyncio._CoroutineLike
else:
    CoroutineType = Awaitable

from ..schema import SearchResult, HtmlResult
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
]

SCRAPINGBEE_API = "https://app.scrapingbee.com/api/v1/"


class PageDowloader:
    def __init__(self, session: aiohttp.ClientSession, concurrent_page_download: int, timeout: float) -> None:
        self.timeout = aiohttp.ClientTimeout(timeout)
        self.session = session
        self.semaphore = asyncio.Semaphore(concurrent_page_download)
        self._page_download_limit = concurrent_page_download
        self._scrapingbee_key = os.getenv("SCRAPINGBEE_API_KEY")
        self._max_retry = int(os.getenv("SCRAPINGBEE_MAX_RETRY", "1"))  # Giảm từ 3 xuống 1 để tiết kiệm credits
        self._delay_min = float(os.getenv("SCRAPINGBEE_DELAY_MIN", "1"))
        self._delay_max = float(os.getenv("SCRAPINGBEE_DELAY_MAX", "3"))
        self._api_call_count = 0  # Đếm số lần gọi API để theo dõi credits
        self._premium_api_call_count = 0  # Đếm số lần dùng premium_proxy (tốn 10 credits)
        # Cache để tránh download lại cùng URL (trong cùng session)
        self._cache: dict[str, HtmlResult] = {}
        # Danh sách domains cần premium_proxy (có thể bị chặn)
        self._premium_domains = {
            "uet.edu.vn", "uet.vnu.edu.vn", "www.uet.vnu.edu.vn",
            "hust.edu.vn", "www.hust.edu.vn",
            "vnu.edu.vn", "www.vnu.edu.vn"
        }
        self._wp_selectors = [
            "article",
            "div.entry-content",
            "div.td-post-content",
            "div.single-content",
            "div.post-content",
        ]
    async def _run_jobs(self, jobs: list[CoroutineType], k_pages: int):
        """
        This function attempt to run jobs in parallel.\n
        It would stop when reach k_pages, and keep input order.\n
        PARALLEL: Tất cả tasks chạy song song, không chờ tuần tự.
        """
        initial_count = self._api_call_count
        print(f"[Page download] Attempt to download {k_pages} pages from {len(jobs)} urls (PARALLEL, tối đa {k_pages} request cùng lúc)")
        page_count = 0
        results: list[None | HtmlResult] = [None] * len(jobs)
        completed_indices = set()

        try:
            pending: dict[asyncio.Task, int] = {}
            next_job_idx = 0

            def maybe_fill_tasks():
                nonlocal next_job_idx
                while (
                    next_job_idx < len(jobs)
                    and len(pending) < k_pages
                    and page_count + len(pending) < k_pages
                ):
                    task = asyncio.create_task(jobs[next_job_idx])
                    pending[task] = next_job_idx
                    next_job_idx += 1

            # Khởi tạo: chỉ gửi tối đa k_pages requests và đảm bảo không vượt quá nhu cầu
            maybe_fill_tasks()
            
            while pending and page_count < k_pages:
                # Đợi task đầu tiên hoàn thành
                done, pending_tasks = await asyncio.wait(
                    pending.keys(),
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Xử lý các tasks đã hoàn thành
                for task in done:
                    idx = pending.pop(task)
                    try:
                        result = await task
                        results[idx] = result
                        # Chỉ tính là thành công nếu có html (không rỗng)
                        if result is not None and result.get("html", "").strip():
                            page_count += 1
                            completed_indices.add(idx)
                    except asyncio.CancelledError:
                        results[idx] = None
                    except Exception as e:
                        results[idx] = None
                        print(f"[Page download] Task {idx} error: {str(e)[:50]}")
                    finally:
                        # Khi một task hoàn thành (kể cả thất bại), mới gửi request tiếp theo
                        if page_count < k_pages:
                            maybe_fill_tasks()
                
                # Nếu đã đủ k_pages, cancel các tasks còn lại
                if page_count >= k_pages:
                    cancelled_count = len(pending)
                    for cancel_task in pending.keys():
                        if not cancel_task.done():
                            cancel_task.cancel()
                    # Đợi tất cả tasks hoàn thành (kể cả cancelled)
                    await asyncio.gather(*pending.keys(), return_exceptions=True)
                    if cancelled_count > 0:
                        print(f"[Page download] Đã cancel {cancelled_count} tasks (có thể đã gửi request, ScrapingBee vẫn tính credits)")
                    break
        finally:
            # Đảm bảo tất cả tasks đã được xử lý
            if pending:
                await asyncio.gather(*pending.keys(), return_exceptions=True)
        
        requests_sent = self._api_call_count - initial_count
        print(f"[Page download] Tổng requests đã gửi: {requests_sent} (bao gồm cả cancelled)")
        return results
    async def _null_task(self):
        return None
    async def download(self, search_results: list[SearchResult], k_pages: int, include_pdf: bool, include_image: bool) -> list[HtmlResult]:
        """Download up to k_pages from input list"""
        initial_api_count = self._api_call_count
        self._initial_premium_count = self._premium_api_call_count
        ssl = os.getenv("WEB_SEARCH_SSL", "True").lower() in ("true", "1")
        # Tạo jobs cho toàn bộ URL nhưng _run_jobs chỉ gửi tối đa k_pages requests cùng lúc
        max_jobs = len(search_results)
        jobs = []
        for i, search_result in enumerate(search_results[:max_jobs]):
            if search_result["url"].endswith(".pdf"):
                if include_pdf:
                    jobs.append(self._handle_file_task(search_result))
                else:
                    jobs.append(self._null_task())
            else:
                jobs.append(self._download_task(ssl, search_result))
        if len(search_results) > max_jobs:
            print(f"[Page download] Giới hạn jobs: {len(jobs)}/{len(search_results)} (tránh gửi quá nhiều requests)")
        job_results =  await self._run_jobs(jobs, k_pages)
        html_results: list[HtmlResult] = []
        for job_result in job_results:
            if job_result:
                html_results.append(job_result)
        credits_used = self._api_call_count - initial_api_count
        premium_used = self._premium_api_call_count - (getattr(self, '_initial_premium_count', 0))
        regular_used = credits_used - premium_used
        total_credits_cost = regular_used * 1 + premium_used * 10  # Premium tốn 10 credits
        
        print(f"[Page download] Success download {len(html_results)} pages")
        print(f"[Page download] ScrapingBee requests: {credits_used} (regular: {regular_used}, premium: {premium_used})")
        print(f"[Page download] ScrapingBee credits used: {total_credits_cost} (regular: {regular_used}x1, premium: {premium_used}x10)")
        return html_results
    async def _handle_file_task(self, search_result: SearchResult) -> HtmlResult | None:
        # Async only to make compatible
        if search_result["url"].endswith(".pdf"):
            result: HtmlResult = {
                **search_result,
                "html": f'[{search_result["title"]}]({search_result["url"]})'
            }
            return result
    def _clean_html(self, html: str) -> str:
        """Clean HTML nhưng giữ nguyên HTML structure (không convert sang plain text) để preserve table format"""
        soup = BeautifulSoup(html, "html.parser")
        # Xóa các tag không cần thiết nhưng giữ HTML structure
        for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "aside"]):
            tag.decompose()
        for element in soup(text=lambda x: isinstance(x, Comment)):
            element.extract()
        
        # Tìm content area nhưng giữ HTML structure
        for selector in self._wp_selectors:
            target = soup.select_one(selector)
            if target:
                # Kiểm tra xem có content không (có table hoặc text dài)
                has_table = target.find("table") is not None
                text_preview = target.get_text(separator=" ", strip=True)
                if len(text_preview) > 200 or has_table:
                    return str(target)
        
        # Tìm best candidate nhưng giữ HTML
        candidates = soup.find_all(["div", "main", "section", "article"], recursive=True)
        best = None
        best_score = 0
        for candidate in candidates:
            has_table = candidate.find("table") is not None
            text_preview = candidate.get_text(separator=" ", strip=True)
            score = len(text_preview) + (1000 if has_table else 0)  # Ưu tiên có table
            if score > best_score:
                best_score = score
                best = candidate
        
        if best and best_score > 200:
            return str(best)
        
        # Fallback: trả về main/body nhưng giữ HTML
        target = soup.find("main") or soup.body or soup
        return str(target)

    def _needs_premium_proxy(self, url: str) -> bool:
        """Kiểm tra URL có cần premium_proxy không (dựa vào domain)"""
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc.lower()
            return any(premium_domain in domain for premium_domain in self._premium_domains)
        except:
            return False
    
    async def _scrapingbee_fetch(self, search_result: SearchResult) -> HtmlResult | None:
        if not self._scrapingbee_key:
            print("[Page downloader] Missing SCRAPINGBEE_API_KEY")
            return None
        
        url = search_result["url"]
        
        # Kiểm tra cache trước
        if url in self._cache:
            print(f"[Page download] Cache hit: {url[:60]}...")
            return self._cache[url]
        
        # Strategy: Thử không dùng premium_proxy trước (1 credit), nếu fail thì dùng premium_proxy (10 credits)
        needs_premium = self._needs_premium_proxy(url)
        use_premium_first = needs_premium  # Nếu domain cần premium, dùng luôn
        
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        
        # Thử 1: Không dùng premium_proxy (1 credit)
        if not use_premium_first:
            params = {
                "api_key": self._scrapingbee_key,
                "url": url,
                "render_js": "false",
                "premium_proxy": "false",  # Thử không dùng premium trước
            }
            try:
                self._api_call_count += 1
                async with self.session.get(
                    SCRAPINGBEE_API,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                ) as response:
                    html = await response.text()
                    if response.status == 200:
                        cleaned_text = self._clean_html(html)
                        if cleaned_text:
                            result = {
                                **search_result,
                                "html": cleaned_text,
                            }
                            self._cache[url] = result  # Cache kết quả - đảm bảo không download lại
                            print(f"[Page download] ✓ Thành công (không premium): {url[:60]}...")
                            return result
                    # Nếu bị chặn (402, 403, 429) → thử premium_proxy
                    # 402 = Payment required (có thể do rate limit, thử premium)
                    # 403 = Forbidden (bị chặn, thử premium)
                    # 429 = Too Many Requests (rate limit, thử premium)
                    if response.status in [402, 403, 429]:
                        print(f"[Page download] Bị chặn/rate limit (status {response.status}), thử premium_proxy: {url[:60]}...")
                    else:
                        print(f"[Page download] Lỗi {response.status}, thử premium_proxy: {url[:60]}...")
            except Exception as e:
                print(f"[Page download] Exception, thử premium_proxy: {str(e)[:50]}...")
        
        # Thử 2: Dùng premium_proxy (10 credits) - chỉ khi cần
        params = {
            "api_key": self._scrapingbee_key,
            "url": url,
            "render_js": "false",
            "premium_proxy": "true",  # Dùng premium_proxy
        }
        
        for attempt in range(1, self._max_retry + 1):
            try:
                self._api_call_count += 1
                self._premium_api_call_count += 1  # Đếm premium requests
                async with self.session.get(
                    SCRAPINGBEE_API,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                ) as response:
                    html = await response.text()
                    if response.status == 200:
                        cleaned_text = self._clean_html(html)
                        if cleaned_text:
                            result = {
                                **search_result,
                                "html": cleaned_text,
                            }
                            self._cache[url] = result  # Cache kết quả
                            print(f"[Page download] ✓ Thành công (premium): {url[:60]}...")
                            return result
                        print(f"[Page downloader] Empty body after cleaning: {url}")
                        # Return None để không tính là thành công, cho phép retry hoặc skip
                        return None
                    elif response.status == 401:
                        error_msg = html[:200] if html else "No error message"
                        print(f"[Page download] Error 401 (Unauthorized) via ScrapingBee: {url[:60]}...")
                        print(f"[Page download] ScrapingBee error details: {error_msg}")
                        return None
                    elif response.status == 402:
                        # 402 trong premium có thể là hết credits thật
                        # Nhưng cũng có thể là rate limit, nên không retry
                        print(f"[Page download] ScrapingBee: Payment required (status 402) - có thể hết credits hoặc rate limit")
                        return None
                    else:
                        print(f"[Page download] Error {response.status} via ScrapingBee: {url[:60]}... (không retry)")
                        return None
            except asyncio.CancelledError:
                # Task bị cancel - request đã được đếm ở trên, ScrapingBee vẫn tính credits
                print(f"[Page downloader] Cancelled (đã gửi request): {search_result['url'][:60]}...")
                raise  # Re-raise để caller biết task bị cancel
            except asyncio.TimeoutError:
                # Timeout - request đã được đếm ở trên, ScrapingBee vẫn tính credits
                print(f"[Page downloader] Timeout via ScrapingBee: {search_result['url']} (không retry)")
                return None
            except Exception as e:
                # Exception - request đã được đếm ở trên
                if attempt < self._max_retry:
                    print(f"[Page downloader] Error via ScrapingBee (attempt {attempt}/{self._max_retry}): {str(e)[:100]}")
                    await asyncio.sleep(random.uniform(self._delay_min, self._delay_max))
                else:
                    print(f"[Page downloader] Error via ScrapingBee (final): {str(e)[:100]}")
                    return None
            return None
    async def _download_task(self, ssl: bool, search_result: SearchResult) -> HtmlResult | None:
        async with self.semaphore:
            return await self._scrapingbee_fetch(search_result)