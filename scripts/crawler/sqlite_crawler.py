import concurrent.futures
from typing import TYPE_CHECKING
import concurrent
if TYPE_CHECKING:
    from pack import *
else:
    try:
        from pack import *
    except ImportError:
        from .pack import *
        
async def run_single(info: GeneralInfo, executor: concurrent.futures.ThreadPoolExecutor):
    """Run a single school crawler
    Args:
        info (GeneralInfo): School info
    """
    filter = BasicFilter()
    priority = BasicPriority(info["Website"])
    pq = UrlPriorityQueue(
        filter,
        priority
    )
    db_path = f"data/sqlite/sqlite.db"
    logger = SQLiteLogger(int(info["Id"]), db_path, executor)
    consumer = SQLiteConsumer(int(info["Id"]), db_path, executor)
    
    crawler = SchoolCrawler(
        info=info,
        pq=pq,
        logger=logger,
        consumer=consumer,
        page_limit=10,
        concurrent_limit=4,
        max_retry=3,
        timeout=30
    )
    print(f"Start {info["Tên trường"]}")
    await crawler.run()
    print(f"Completed {info["Tên trường"]}")
    
    
def run_all():
    """Schedule and run all crawlers
    """
    data = get_uni_info()
    max_concurrent = 32
    # Scheduler (Single thread)
    db_path = "sqlite:///data/sqlite/sqlite.db"
    create(db_path, True)
    add_schools(db_path, data)
    db_executor = concurrent.futures.ThreadPoolExecutor(1) # Only support 1 thread
    async def main():
        semaphore = asyncio.Semaphore(max_concurrent)
        async def task(info):
            async with semaphore:
                await run_single(info, db_executor)
        jobs = []
        for info in data:
            jobs.append(asyncio.create_task(task(info)))
        
        await asyncio.gather(*jobs)
    asyncio.run(main())
    
if __name__ == "__main__":
    run_all()