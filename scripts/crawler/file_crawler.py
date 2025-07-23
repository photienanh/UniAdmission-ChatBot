from typing import TYPE_CHECKING
import concurrent
if TYPE_CHECKING:
    from pack import *
else:
    try:
        from pack import *
    except ImportError:
        from .pack import *
    
async def run_single(info: GeneralInfo):
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
    logger = FileLogger(f"data/crawl_log/{info["Id"]}")
    os.makedirs(f"data/school_raw/{info["Id"]}")
    file_consumer = FileConsumer(f"data/school_raw/{info["Id"]}")
    crawler = SchoolCrawler(
        info=info,
        pq=pq,
        logger=logger,
        consumer=file_consumer,
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
    max_concurrent = 8
    # Scheduler (Single thread)
    
    async def main():
        semaphore = asyncio.Semaphore(max_concurrent)
        async def task(info):
            async with semaphore:
                await run_single(info)
        jobs = []
        for info in data:
            jobs.append(asyncio.create_task(task(info)))
        
        await asyncio.gather(*jobs)
    asyncio.run(main())
    
if __name__ == "__main__":
    run_all()