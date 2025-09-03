from langchain_core.documents import Document

from ..config import MergeTableConfig
class MergeTable:
    def __init__(self, config: MergeTableConfig) -> None:
        self.config = config
    def __call__(self, total_docs: list[Document], relevant_docs: list[Document]) -> list[Document]:
        """Try to merge splitted table. Work on multi pages."""
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
            lines = chunk.page_content.splitlines()
            page_result_chunks: list[Document] = []
            if (page_index, chunk_index) not in retrived_keys:
                retrived_keys.add((page_index, chunk_index))
                page_result_chunks.append(chunk)
            # Check for table at start of this chunk
            if lines[0].count("|") >= self.config.separator_threshold: 
                from_ = max(0, chunk_index-self.config.k_max_previous)
                to_ = chunk_index
                for current_index in reversed(list(range(from_, to_))):
                    key = (page_index, current_index)
                    if key in lookup_table:
                        current_chunk = lookup_table[key]
                        # Check if end of previous chunk is table
                        if current_chunk.page_content.splitlines()[-1].count("|") >= self.config.separator_threshold:
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
                    key = (page_index, current_index)
                    if key in lookup_table:
                        current_chunk = lookup_table[key]
                        # Check if start of previous chunk is table
                        if current_chunk.page_content.splitlines()[0].count("|") >= self.config.separator_threshold:
                            if key not in retrived_keys:
                                retrived_keys.add(key)
                                page_result_chunks.append(current_chunk)
                        else:
                            break
                    else:
                        break
            result.extend(page_result_chunks)
        return result