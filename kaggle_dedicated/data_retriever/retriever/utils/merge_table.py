from ...schema import RagSource
from ...config import MergeTableConfig
class MergeTable:
    def __init__(self, config: MergeTableConfig) -> None:
        self.config = config
    def merge(self, total_sources: list[RagSource], relevant_sources: list[RagSource]) -> list[RagSource]:
        """Try to merge splitted table. Work on a single page, not support multi pages."""
        # Mapping table for lookup with chunk index
        lookup_table = {source["chunk_index"]:source for source in total_sources}
        # Mark retrived key
        retrived_keys: set[int] = set()
        result: list[RagSource] = []
        for source in relevant_sources:
            chunk_index = source["chunk_index"]
            lines = source["text"].splitlines()
            page_result_chunks: list[RagSource] = []
            if chunk_index not in retrived_keys:
                retrived_keys.add(chunk_index)
                page_result_chunks.append(source)
            # Check for table at start of this chunk
            if lines[0].count("|") >= self.config.separator_threshold: 
                from_ = max(0, chunk_index-self.config.k_max_previous)
                to_ = chunk_index
                for current_index in reversed(list(range(from_, to_))):
                    key = current_index
                    if key in lookup_table:
                        current_chunk = lookup_table[key]
                        # Check if end of previous chunk is table
                        if current_chunk["text"].splitlines()[-1].count("|") >= self.config.separator_threshold:
                            if key not in retrived_keys:
                                retrived_keys.add(key)
                                page_result_chunks.insert(0, current_chunk)
                        else:
                            break
                    else:
                        break
            # Check for table at end of this chunk
            if lines[-1].count("|") >= self.config.separator_threshold: 
                from_ = chunk_index
                to_ = chunk_index+self.config.k_max_next+1
                for current_index in range(from_, to_):
                    key = current_index
                    if key in lookup_table:
                        current_chunk = lookup_table[key]
                        # Check if start of previous chunk is table
                        if current_chunk["text"].splitlines()[0].count("|") >= self.config.separator_threshold:
                            if key not in retrived_keys:
                                retrived_keys.add(key)
                                page_result_chunks.append(current_chunk)
                        else:
                            break
                    else:
                        break
            result.extend(page_result_chunks)
        return result