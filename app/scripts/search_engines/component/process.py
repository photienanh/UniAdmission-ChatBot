import requests
from engines import PreProcessedResult, ProcessedResult

class Processor:
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
    def __html(self, url: str) -> str:
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.text
    
    def __call__(self, input: PreProcessedResult) -> ProcessedResult | None:
        
        result: ProcessedResult = {
            "url": input["url"],
            "title": input["title"],
            "description": input["description"],
            "timestamp": input["timestamp"],
            "html": input["html"],
            "index": input["index"],
            "main_content": "",
            "image_content": [],
            "pdf_content": []
        }
        return result
