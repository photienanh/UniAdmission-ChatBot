import os
import datetime
import aiofiles
from typing import Optional
from .common import *

class FileLogger(ILogger):
    def __init__(self, log_folder: str):
        self.error_log_file = os.path.join(log_folder, "error.txt")
        self.success_log_file = os.path.join(log_folder, "success.txt")
        self.travel_log_file = os.path.join(log_folder, "travel.txt")
        os.makedirs(log_folder, exist_ok=True)
        if os.path.exists(self.error_log_file): os.remove(self.error_log_file)
        if os.path.exists(self.travel_log_file): os.remove(self.travel_log_file)
        if os.path.exists(self.success_log_file): os.remove(self.success_log_file)
    async def error(self, item: UrlItem, error: Exception):
        now = datetime.datetime.now()
        now = now.strftime("%H:%M:%S")
        log = f"{now}|{item.key.index:>5}|{item.key.retry:>2}|{item.url}|{error}\n"
        async with aiofiles.open(self.error_log_file, 'a', encoding="utf-8") as file:
            await file.write(log)    
    async def success(self, item: UrlItem):
        log = f"{item.key.index}|{item.url}\n"
        async with aiofiles.open(self.success_log_file, 'a', encoding="utf-8") as file:
            await file.write(log)
    async def travel(self, url: str, item: Optional[UrlItem]):
        if item != None:
            log = f"True|{item.key.index:>5}|{item.key.retry:>2}|{item.key.score}|{item.url}\n"
        else:
            log = f"False|{url}\n"
        async with aiofiles.open(self.travel_log_file, 'a', encoding="utf-8") as file:
            await file.write(log)