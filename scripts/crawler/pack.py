import pickle
import asyncio
import os
import time
try:
    # Absolute import
    from utility import UrlPriorityQueue, CrawlerResult, SchoolCrawler, get_uni_info, create, add_schools
    from config import BasicFilter, BasicPriority, FileLogger, FileConsumer, SQLiteLogger, SQLiteConsumer
    from format import GeneralInfo
except ImportError:
    # Relative import
    from .utility import UrlPriorityQueue, CrawlerResult, SchoolCrawler, get_uni_info, create, add_schools
    from .config import BasicFilter, BasicPriority, FileLogger, FileConsumer, SQLiteLogger, SQLiteConsumer
    from .format import GeneralInfo