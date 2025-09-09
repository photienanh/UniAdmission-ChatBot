from ...schema import RagSource
from ...config import MergeNeighborConfig
class MergeNeighbor:
    def __init__(self, config: MergeNeighborConfig) -> None:
        self.config = config
    def merge(self, total_sources: list[RagSource], relevant_sources: list[RagSource]) -> list[RagSource]:
        result: list[RagSource] = []
        """Retrive neighbor chunks to relevant chunks. Work on a single page, not support multi pages."""
        # Mapping table for lookup with chunk index
        lookup_table = {source["chunk_index"]:source for source in total_sources}
        # Mark retrived key
        retrived_keys: set[int] = set()
        result: list[RagSource] = []
        for source in relevant_sources:
            chunk_index = source["chunk_index"]
            from_ = max(0, chunk_index-self.config.k_previous_chunks)
            to_ = chunk_index + self.config.k_next_chunks + 1 # We don't know max length
            for current_index in range(from_, to_):
                key = current_index
                if key in lookup_table and key not in retrived_keys:
                    retrived_keys.add(key)
                    result.append(lookup_table[key])
        return result