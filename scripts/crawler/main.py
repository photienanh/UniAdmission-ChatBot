from sqlite_crawler import run_all
from get_basic_info import download_info
import asyncio
from utility import run_coroutine
import os


run_coroutine(download_info)
os.makedirs("data/sqlite", exist_ok=True)
run_all()

