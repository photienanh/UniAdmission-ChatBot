try:
    # Run code in absolute mode
    from utility import (
        IFilter, IPriority, ILogger, UrlItem, UrlKey, CrawlerResult, IConsumer
    )
except ImportError:
    # Run code in relative mode
    from ..utility import (
        IFilter, IPriority, ILogger, UrlItem, UrlKey, CrawlerResult, IConsumer
    )
__all__ = [
    "UrlKey", "IFilter", "IPriority", "ILogger", "UrlItem", "CrawlerResult", "IConsumer"
]