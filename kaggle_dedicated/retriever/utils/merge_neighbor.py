from langchain_core.documents import Document

from ..config import MergeNeighborConfig
class MergeNeighbor:
    def __init__(self, config: MergeNeighborConfig) -> None:
        self.config = config
    def __call__(self, total_docs: list[Document], relevant_docs: list[Document]) -> list[Document]:
        result: list[Document] = []
        """Retrive neighbor chunks to relevant chunks. Work on multi pages."""
        # Mapping table for lookup with page and chunk index
        lookup_table = {
            (chunk.metadata["page_index"], chunk.metadata["chunk_index"]): chunk for chunk in total_docs
        }
        # Mark retrived key
        retrived_keys: set[tuple[int, int]] = set()
        result: list[Document] = []
        for chunk in relevant_docs:
            page_index = chunk.metadata["page_index"]
            chunk_index = chunk.metadata["chunk_index"]
            from_ = max(0, chunk_index-self.config.k_previous_chunks)
            to_ = chunk_index + self.config.k_next_chunks + 1 # We don't know max length
            for current_index in range(from_, to_):
                key = (page_index, current_index)
                if key in lookup_table and key not in retrived_keys:
                    retrived_keys.add(key)
                    result.append(lookup_table[key])
        return result