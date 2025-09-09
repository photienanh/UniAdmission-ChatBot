from flashrank import Ranker, RerankRequest

from ..schema import RagSource
from ..config import ChunkRankerConfig

class ChunkRanker:
    """Wrapper class for rerank chunks"""
    def __init__(self, chunk_config: ChunkRankerConfig) -> None:
        self.chunk_config = chunk_config
        self.ranker = Ranker(chunk_config.ranker_name, max_length=chunk_config.max_length)
    def rerank_chunks(self, sources: list[RagSource], query: str, relative_threshold: float = 0.5) -> list[RagSource]:
        """Perform rerank (Per page)."""
        # For lookup when process result
        id_source = {index: source for index, source in enumerate(sources)} 
        # Convert to flashrank format
        passages = [{
            "id": index,
            "text": source["text"]
        } for index, source in enumerate(sources)]
        request = RerankRequest(query=query, passages=passages)
        results = self.ranker.rerank(request)
        max_score = 0
        for result in results:
            max_score = max(max_score, result["score"])
        score_threshold = 0 if max_score == 0 else max_score * relative_threshold
        
        if self.chunk_config.keep_order:
            results = sorted(results, key=lambda item:item["id"])

        valid_sources: list[RagSource] = []
        for result in results:
            if result["score"] >= score_threshold:
                valid_sources.append(id_source[result["id"]])
        return valid_sources