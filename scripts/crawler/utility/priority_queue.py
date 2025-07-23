import heapq
from typing import NamedTuple, Optional

class UrlKey(NamedTuple):
    score: float
    level: int
    index: int
    retry: int
class UrlItem(NamedTuple):
    key: UrlKey
    from_url: str
    url: str
    html: str
    
class IFilter:
    def filter(self, recorded: set[str], url: str, text: str) -> bool:
        raise NotImplementedError()
class IPriority:
    def score(self, url: str, text: str) -> float:
        raise NotImplementedError()
    def priority(self, key: UrlKey) -> float | tuple[float, ...]:
        raise NotImplementedError()
    def neg_priority(self, key: UrlKey) -> float | tuple[float, ...]:
        priority = self.priority(key)
        if isinstance(priority, tuple):
            result = tuple(-p for p in priority)
            return result
        else:
            return -priority
class UrlPriorityQueue:
    def __init__(
        self,
        filter: IFilter,
        priority: IPriority
    ):
        self.__data: list = []
        self.filter = filter
        self.priority = priority
        self.index_count = 0
        self.recorded = set([])
    def add(self, level: int, from_url: str, url: str, text: str) -> Optional[UrlItem]:
        if self.filter.filter(self.recorded, url, text):
            self.recorded.add(url)
            self.index_count += 1
            score = self.priority.score(url, text)
            key = UrlKey(score, level, self.index_count, 0)
            item = UrlItem(key, from_url, url, text)
            priority = self.priority.neg_priority(key)
            heapq.heappush(self.__data, (priority, item)) # Max heap
            return item
    def retry(self, item: UrlItem) -> UrlItem:
        key = UrlKey(item.key.score, item.key.level, item.key.index, item.key.retry + 1)
        item = UrlItem(key, item.from_url, item.url, item.html)
        priority = self.priority.neg_priority(key)
        heapq.heappush(self.__data, (priority, item)) # Max heap
        return item
    def pop(self) -> tuple[float, UrlItem]:
        item = heapq.heappop(self.__data)
        return item
    def __len__(self) -> int:
        return len(self.__data)