from .common import IConsumer, ProcessedResult
import aiofiles
import os

class FileConsumer(IConsumer):
    def __init__(self, output_folder: str, min_threshold: int = 2000) -> None:
        self.output_folder = output_folder
        self.min_threshold = min_threshold
    async def consume(self, id: str | int, data: ProcessedResult):
        if len(data.text) < self.min_threshold: return
        file_path = os.path.join(self.output_folder, f"{id}.html")
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as file:
            await file.write(data.text)
            
