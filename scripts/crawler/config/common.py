try:
    # Run code in absolute mode
    from utility import (
        IFilter, IPriority, ILogger, UrlItem, UrlKey
    )
except ImportError:
    # Run code in relative mode
    from ..utility import (
        IFilter, IPriority, ILogger, UrlItem, UrlKey
    )
__all__ = [
    "UrlKey", "IFilter", "IPriority", "ILogger", "UrlItem"
]