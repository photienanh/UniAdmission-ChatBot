from concurrent.futures import ThreadPoolExecutor

from .common import *
import os
import aiofiles
    
        
class FileConsumer(IConsumer):
    def __init__(self, folder_path: str):
        os.makedirs(folder_path, exist_ok=True)
        self.folder_path = folder_path
    async def consume(self, data: CrawlerResult):
        save_path = os.path.join(self.folder_path, f"{data.doc_index}.html")
        try:
            async with aiofiles.open(save_path, 'w', encoding='utf-8') as file:
                await file.write(f"<!-- Source:{data.url} -->\n")
                await file.write(data.html)
        except Exception as e:
            print(f"Failed to save {data.url} | {e}")