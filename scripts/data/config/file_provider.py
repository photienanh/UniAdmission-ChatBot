from .common import IProvider, ProcessInput
import aiofiles
import re
import os

URL_PATTERN = re.compile(r'<!--\sSource:(.*?)\s-->')
class FileProvider(IProvider):
    def __init__(self, input_path: str) -> None:
        self.input_path = input_path
    async def provide(self, index: int, id: str) -> ProcessInput:
        file_path = os.path.join(self.input_path, f"{id}.html")
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            html = await file.read()
        #<!-- Source:http://hocvienamnhachue.edu.vn/ -->
        url: str = re.findall(URL_PATTERN, html)[0]
        return ProcessInput(index, url, html)