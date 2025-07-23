from sqlite_crawler import run_all
from get_basic_info import download_info
import asyncio

async def main():
    await download_info()
    run_all()
    
asyncio.run(main())