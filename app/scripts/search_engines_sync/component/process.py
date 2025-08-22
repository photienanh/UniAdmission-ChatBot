from ..engines import PreProcessedResult, ProcessedResult

class Processor:
    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
    
    def __call__(self, input: PreProcessedResult) -> ProcessedResult | None:
        # Implement here
        
        result: ProcessedResult = {
            "url": input["url"],
            "title": input["title"],
            "description": input["description"],
            "timestamp": input["timestamp"],
            "html": input["html"],
            "index": input["index"],
            "main_content": input["extracted_content"],
            "image_content": [],
            "pdf_content": []
        }
        return result