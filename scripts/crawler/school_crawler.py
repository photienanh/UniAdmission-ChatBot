from format import GeneralInfo, TITLES
import pickle
import time
from utility import CrawlEngine
import math
import asyncio
import re
import queue
from collections import deque
import os
import json
from format import GeneralInfo, TITLES
import pickle
import heapq
from urllib.parse import urlparse
from typing import NamedTuple
import aiofiles
import datetime
from typing import Callable, Any


class UrlKey(NamedTuple):
    score: float
    level: int
    index: int
    retry: int
class UrlItem(NamedTuple):
    key: UrlKey
    url: str
    text: str
class AnchorData(NamedTuple):
    href: str
    text: str
def compute_priority(key: UrlKey):
    return (-key.score / key.level if key.level != 0 else 0, -key.index, -key.retry)
def get_root_url(url: str):
    return "/".join(url.split("/")[:3])
def url_reconstructor(path_url: str, url:str):
    if len(url) > 0 and url[-1] == "#":
        url = url[:-1]
    root_url = get_root_url(path_url)
    """
    Three type:
    1. Full url: http....
    2. Relative url: /home....
    3. Query: ?
    """
    if url.startswith("http://") or url.startswith("https://"):
        result = url
    elif url.startswith("/"):
        result = root_url + url
    else:
        result = path_url + url
    if "#" in result.split("/")[-1]:
        result = "#".join(result.split("#")[:-1])
    return result
def extract_anchor_data(html: str) -> list[AnchorData]:
    matches = re.findall(r'<a(.*?)/a>', html, re.DOTALL) # Shortest match, so it capture <a></a>
    urls = []
    for match in matches:
        hrefs = re.findall(r'href="(.*?)"', match)
        texts = re.findall(r'>(.*?)<', match)
        if hrefs:
            urls.append(AnchorData(hrefs[0], texts[0] if texts else ""))
    return urls
class SchoolCrawler:
    def __init__(self, 
            info: GeneralInfo,
            filter: Callable[[set, str, str], bool],
            score_compute: Callable[[str, str], float],
            save_folder: str = "data/school_raw",
            log_folder: str = "data/crawl_log",
            page_limit: int = 500,
            concurrent_limit: int = 4,
            max_retry: int = 3,
            timeout: float = 30
        ):
        """
        Filter accept (recorded, url, text)
        Score compute accept (url, text)
        """
        self.score_compute = score_compute
        self.filter = filter
        self.info = info
        self.engine = CrawlEngine(concurrent_limit, timeout)
        self.url_queue: list[tuple[float, UrlItem]] = []
        self.count = 0
        self.index_count = 0
        self.save_folder: str = os.path.join(save_folder, str(info["Id"]))
        self.page_limit = page_limit
        self.max_rety = max_retry
        self.failed_count = 0
        self.recorded = set([])
        self.pdf_recorded = set([])
        self.error_log_file: str = os.path.join(log_folder, str(info["Id"]), "error.txt")
        self.travel_log_file: str = os.path.join(log_folder, str(info["Id"]), "travel.txt")
        self.success_log_file: str = os.path.join(log_folder, str(info["Id"]), "success.txt")
        self.pdf_log_file: str = os.path.join(log_folder, str(info["Id"]), "pdf_urls.txt")
        os.makedirs(self.save_folder, exist_ok=True)
        os.makedirs(os.path.join(log_folder, str(info["Id"])), exist_ok=True)
        if os.path.exists(self.pdf_log_file): os.remove(self.pdf_log_file)
        if os.path.exists(self.error_log_file): os.remove(self.error_log_file)
        if os.path.exists(self.travel_log_file): os.remove(self.travel_log_file)
        if os.path.exists(self.success_log_file): os.remove(self.success_log_file)
    def _add_url(self, url: str, level: int, text: str): # Use reconstructed url
        # print(f"Add {url}")
        self.index_count += 1
        score = self.score_compute(url, text)
        key = UrlKey(score, level, self.index_count, 0)
        item = UrlItem(key, url, text)
        priority = compute_priority(key)
        heapq.heappush(self.url_queue, (priority, item))
        return item
    def _retry_item(self, item: UrlItem):
        key = UrlKey(item.key.score, item.key.level, item.key.index, item.key.retry+1)
        item = UrlItem(key, item.url, item.text)
        priority = compute_priority(key)
        heapq.heappush(self.url_queue, (priority, item))
    def _pop_url(self):
        item = heapq.heappop(self.url_queue)
        # print(f"Remove {item.url}")
        return item
    async def save(self, url: str, text: str):
        replace_map = {
            "https://": "",
            "http://": "",
            "/": "_",
            ":": "_",
            "?": "_",
            ".": "_"
        }
        valid_name = url
        for key, value in replace_map.items():
            valid_name = valid_name.replace(key, value)
        save_path = os.path.join(self.save_folder, valid_name + ".html")
        try:
            async with aiofiles.open(save_path, 'w', encoding='utf-8') as file:
                await file.write(text)
        except Exception as e:
            print(f"Failed to save {save_path}")
    async def run(self):
        await self.engine.start()
        self._add_url(self.info["Website"], 0, "Website")
        self.recorded.add(self.info["Website"])
        # try
        while len(self.url_queue) > 0:
            batch_items: list[UrlItem] = []
            batch_jobs = []
            success_count = 0
            for _ in range(self.engine.limit):
                if len(self.url_queue) > 0:
                    (n_priority, item) = self._pop_url()
                    batch_items.append(item)
                    job = self.engine.get_task(item.url)
                    batch_jobs.append(job)
                    # print(f"Start {n_priority} {item.url}")
            results = await asyncio.gather(*batch_jobs)
            for index, result in enumerate(results):
                item = batch_items[index]
                if isinstance(result, Exception):
                    self.failed_count += 1
                    now = datetime.datetime.now()
                    now = now.strftime("%H:%M:%S")
                    log = f"{now}|{item.key.index:>5}|{item.key.retry:>2}|{item.url}|{result}\n"
                    async with aiofiles.open(self.error_log_file, 'a', encoding="utf-8") as file:
                        await file.write(log)
                    if item.key.retry < self.max_rety:
                        self._retry_item(item)
                else:
                    success_count += 1
                    anchor_data = extract_anchor_data(result)
                    await self.save(item.url, result)
                    log = f"{item.key.index}|{item.url}\n"
                    async with aiofiles.open(self.success_log_file, 'a', encoding="utf-8") as file:
                        await file.write(log)
                    for anchor_item in anchor_data:
                        url = url_reconstructor(item.url, anchor_item.href)
                        if url.endswith(".pdf") and url not in self.pdf_recorded:
                            self.pdf_recorded.add(url)
                            async with aiofiles.open(self.pdf_log_file, 'a', encoding="utf-8") as file:
                                await file.write(f"{item.key.score}, {url}\n")
                        valid = False
                        if url not in self.recorded and self.filter(self.recorded, url, anchor_item.text):
                            self.recorded.add(url)
                            new_item = self._add_url(url, item.key.level+1, anchor_item.text)
                            valid = True
                        if valid:
                            log = f"{valid}|{new_item.key.index:>5}|{new_item.key.retry:>2}|{new_item.key.score}|{new_item.url}\n"
                        else:
                            log = f"{valid}|{url}\n"
                        async with aiofiles.open(self.travel_log_file, 'a', encoding="utf-8") as file:
                            await file.write(log)
                        
            self.count += success_count
            if self.count >= self.page_limit:
                break
            else:
                # print(self.count,  len(self.url_queue))
                pass
        await self.engine.stop()
async def process_single(info: GeneralInfo):
    website = urlparse(info["Website"])
    w_website = website.netloc
    website = website.netloc.replace("www.", "")
    base_website = website.split(".")[0]
    def filter(recored: set, url: str, text: str):
        black_lists = [
            "javascript",
            "youtube.com",
            "zalo.me",
            "tiktok.com",
            "twitter.com",
            "facebook.com",
            ".jpg",
            ".png",
            ".webp",
            ".avif",
            ".ico",
            ".pdf",
            ".txt"
        ]
        if len(url) < 200:
            for block in black_lists:
                if block in url:
                    return False
            return True
        return False
    def priority(url: str, text: str):
        l_text = text.lower()
        priority_map = {
            "tuyển sinh": 100,
            "xét tuyển": 100,
            "đào tạo": 100,
            "chỉ tiêu": 100,
            "học phí": 100,
            "học bổng": 100,
            "số liệu": 50,
            "ba công khai": 150,
            "báo cáo thường niên": 150,
            "cơ cấu": 100,
            "bậc đại học": 100,
            "đào tạo thạc sĩ": 100,
            "đào tạo tiến sĩ": 100,
            "đội ngũ": 90,
            "cán bộ": 90,
            "chế độ": 90,
            "thông tin": 50,
            "giới thiệu": 50,
            "khoa": 60
        }
        min_priority_list = [
            "ảnh",
            "video"
        ]
        for k, v in priority_map.items():
            if k in l_text:
                return v
        if w_website in url:
            return 10
        elif website in url:
            return 9
        elif base_website in url:
            return 8
        else:
            for p in min_priority_list:
                if p in l_text:
                    return 1
            else:
                return 2
    crawler = SchoolCrawler(
        info,
        filter,
        priority,
        page_limit=500,
        concurrent_limit=4
    )
    print(f"Start {info["Tên trường"]}")
    await crawler.run()
    print(f"Completed {info["Tên trường"]}")
if __name__ == "__main__":
    data: list[GeneralInfo] = []
    with open('data/info/info.pkl', 'rb') as file:
        data = pickle.load(file)
    uni_data: list[GeneralInfo] = []
    for item in data:
        if item['Loại hình cơ sở đào tạo'] in ("Trường đại học", "Đại học","Học viện"):
            uni_data.append(item)
        else:
            # print(item['Loại hình cơ sở đào tạo']) 
            pass
    print(len(uni_data))  
    # index = 4
    # print(uni_data[index])

    async def main():
        max_concurrent = 8
        semaphore = asyncio.Semaphore(max_concurrent)
        async def task(info):
            async with semaphore:
                await process_single(info)
        jobs = []
        for info in uni_data:
            jobs.append(asyncio.create_task(task(info)))
        await asyncio.gather(*jobs)
    asyncio.run(main())