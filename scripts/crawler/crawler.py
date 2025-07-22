import pickle
import asyncio
import os
try:
    # Absolute import
    from utility import UrlPriorityQueue, save_html, CrawlerResult, SchoolCrawler
    from config import BasicFilter, BasicPriority, FileLogger
    from format import GeneralInfo
except ImportError:
    # Relative import
    from .utility import UrlPriorityQueue, save_html, CrawlerResult, SchoolCrawler
    from .config import BasicFilter, BasicPriority, FileLogger
    from .format import GeneralInfo
    
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
    async def consumer(data: CrawlerResult):
        await save_html(
            save_folder=f"data/school_raw/{info["Id"]}",
            index=data.success_index,
            url=data.url,
            text=data.html
        )
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
    data: list[GeneralInfo] = []
    with open('data/info/info.pkl', 'rb') as file:
        data = pickle.load(file)
    uni_data: list[GeneralInfo] = [] # Lọc các trường, chỉ lấy đại học và học viện
    for item in data:
        if item['Loại hình cơ sở đào tạo'] in ("Trường đại học", "Đại học","Học viện"):
            uni_data.append(item)
        else:
            # print(item['Loại hình cơ sở đào tạo']) 
            pass
    print(len(uni_data))  
    max_concurrent = 1

    async def main():
        semaphore = asyncio.Semaphore(max_concurrent)
        async def task(info):
            async with semaphore:
                await run_single(info)
        jobs = []
        for info in uni_data:
            jobs.append(asyncio.create_task(task(info)))
        await asyncio.gather(*jobs)
    asyncio.run(main())
    
if __name__ == "__main__":
    run_all()