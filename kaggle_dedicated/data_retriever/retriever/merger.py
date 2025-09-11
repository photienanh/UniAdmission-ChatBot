from ..config import MergeNeighborConfig, MergeTableConfig
from ..schema import RagSource
from .utils import MergeNeighbor, MergeTable

class Merger:
    def __init__(self, neighbor_config: MergeNeighborConfig, table_config: MergeTableConfig) -> None:
        self.neighbor_config = neighbor_config
        self.table_config = table_config
        self._merge_neigbor = MergeNeighbor(neighbor_config)
        self._merge_table = MergeTable(table_config)
    def merge(self, total_sources: list[RagSource], relevant_sources: list[RagSource], merge_table: bool, merge_neighbor: bool) -> list[RagSource]:
        """Merge RagSource inside a single WebSource. We would merge table before neighbor if both are selected."""
        if merge_table:
            relevant_sources = self._merge_table.merge(total_sources, relevant_sources)
        if merge_neighbor:
            relevant_sources = self._merge_neigbor.merge(total_sources, relevant_sources)
        return relevant_sources