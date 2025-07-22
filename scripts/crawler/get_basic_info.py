import asyncio
import re
from typing import get_args
import csv
import json
import pickle
import os

try:
    # Absolute import
    from utility import CrawlEngine
    from format import GeneralInfo, TITLES
except ImportError:
    # Relative import
    from .utility import CrawlEngine
    from .format import GeneralInfo, TITLES

ID_URL = "https://moet.gov.vn/cosogiaoduc/Pages/danh-sach.aspx?search=1&field=Title&asc=True&Page={index}"
INFO_URL = "https://moet.gov.vn/cosogiaoduc/Pages/danh-sach.aspx?ItemID={id}"
OUTPUT_FOLDER = "data/info"

# Support function
def _parse_ids(html: str): # Can be batched, but parse single for simplicify
    matches = re.findall(r'<a\shref="\?ItemID=(\d+)">', html, re.DOTALL) 
    ids = [int(match) for match in matches]
    return ids
# Support function
def _parse_info(html: str) -> GeneralInfo:
    result: GeneralInfo = {}
    matches = re.findall(r'<table\sclass="tbl-chitiet">(.*?)</table>', html, re.DOTALL)
    match = matches[0]
    titles: list[str] = re.findall(r'<td\sclass="td-lable">(.*?)</td>', match, re.DOTALL)
    values: list[str] = re.findall(r'<td>(.*?)</td>', match, re.DOTALL)
    titles.extend(re.findall(r'<td\sclass="td-lable"\sstyle="font-style:italic;">(.*?)</td>', match, re.DOTALL))
    values.extend(re.findall(r'<td\sstyle="font-style:italic;">(.*?)</td>', match, re.DOTALL))
    for index, key in enumerate(titles):
        key = key.replace("- ", "")
        value = values[index]
        result[key] = value #type:ignore (For type check)
    website = result["Website"]
    if website:
        website = re.findall(r">(.*?)</a>", website)[0]
    result["Website"] = website
    return result

# Download all school ids
async def download_ids() -> list[int]:
    """Download all school ids from

    Returns:
        list[int]: list of school ids
    """
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    engine = CrawlEngine(8)
    limit = 100
    ids: list[int] = []
    await engine.start() # Start session
    urls = [ID_URL.format(index=index) for index in range(1, limit)] # Try all jobs, cancel when reach stopping point
    jobs = engine.get_all(urls)
    
    while len(jobs) > 0:
        batch_jobs = []
        for _ in range(engine.limit):
            batch_jobs.append(jobs.pop(0))
        batch_htmls = await asyncio.gather(*batch_jobs)
        stop = False
        for html in batch_htmls:
            batch_ids = _parse_ids(html)
            if len(batch_ids) > 0:
                ids.extend(batch_ids)
            else:
                stop = True # Stop when batch have empty ids
        if stop:
            for job in jobs: # Cancel remaining jobs
                job.cancel()
            break
    await engine.stop() # End session
    
    with open(f"{OUTPUT_FOLDER}/ids.txt", 'w') as file:
        file.write(json.dumps(ids))
    return ids

async def download_info() -> list[GeneralInfo]:
    """Download all school info
    Returns:
        list[GeneralInfo]: list of school infos
    """
    engine = CrawlEngine(16)
    
    await engine.start() # Start session
    ids = await download_ids() # Get all school ids
    urls = [INFO_URL.format(id=id) for id in ids]  # Get url for school info page
    jobs = engine.get_all(urls) # Download jobs
    htmls = await asyncio.gather(*jobs) # Raw .html results
    await engine.stop() # End session
    
    infos: list[GeneralInfo] = [_parse_info(html) for html in htmls] # Parse html to info
    for index, info in enumerate(infos):
        info["Id"] = str(ids[index])
    # Write to csv, for view purpose
    with open(f"{OUTPUT_FOLDER}/info.csv", 'w', newline='\n', encoding='utf-8') as file: 
        writer = csv.DictWriter(file, fieldnames=list(get_args(TITLES)))
        writer.writeheader()
        writer.writerows(infos)
    # Write to pkl, for usable purpose, prevent encode/decode error
    with open(f"{OUTPUT_FOLDER}/info.pkl", 'wb') as file:
        pickle.dump(infos, file)
    return infos
if __name__ == "__main__":
    asyncio.run(download_info()) # Call download when run as main
    
    
__all__ = [ # Limit import * scope
    "download_ids",
    "download_info" 
]