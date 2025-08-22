from typing import Any
from .component import *
from .engines import ProcessedResult
    
from typing import Literal, TYPE_CHECKING
import traceback

class SearchPipeline:
    def __init__(self) -> None:
        self.querier = WebQuery()
        self.downloader = PageDowloader(10)
        self.preprocessor = PreProcessor()
        self.processor = Processor(10)
        self.logger = Logger("web_search_logs")
    def __call__(self, query: str, k: int = 10, in_domain: bool = False, engine_type: Literal["brave", "google"] = "brave") -> list[ProcessedResult]:
        k = max(1, min(10, k)) # Limit to k
        search_k = max(10, k) # Query at least 10
        result: list[ProcessedResult] = []
        self.logger.enable = True
        self.logger.start(query, k, engine_type)
        for search_result in self.querier(query, search_k, in_domain, engine_type):
            try:
                if len(result) >= k: break # Break when reach target
                self.logger.count()
                if search_result == None: continue
                
                self.logger.search(search_result)
                page_result = self.downloader(search_result)
                if page_result == None: continue
                
                self.logger.html(page_result)
                preprocess_result = self.preprocessor(page_result)
                if preprocess_result == None: continue
                
                self.logger.preprocessed(preprocess_result)
                processed_result = self.processor(preprocess_result)
                if processed_result == None: continue
                
                self.logger.processed(processed_result)
                result.append(processed_result)
            except:
                traceback.print_exc()
        return result