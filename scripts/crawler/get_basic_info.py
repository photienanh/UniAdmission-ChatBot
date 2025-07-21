import asyncio
import re
from utility import CrawlEngine
import json
import os
from typing import TypedDict, Dict, Literal, get_args
from .get_info_list import get_ids
import csv

URL = "https://moet.gov.vn/cosogiaoduc/Pages/danh-sach.aspx?ItemID={id}"

TITLES = Literal[
    "Tên trường", 
    "Loại hình cơ sở đào tạo", 
    "Loại trường", 
    "Cơ quan quản lý trực tiếp",
    "Ký hiệu",
    "Tên tiếng Anh",
    "Website",
    "Tỉnh, thành phố",
    "Được kiểm định bởi tổ chức kiểm định chất lượng giáo dục",
    "Ngày cấp giấy chứng nhận kiểm định chất lượng",
    "Ngày hết hạn giá trị của giấy chứng nhận kiểm định chất lượng"
]

GeneralInfo = Dict[TITLES, str]

async def download_single(id: int) -> GeneralInfo:
    engine = CrawlEngine(4)
    await engine.start()
    url = URL.format(id=id)
    text = await engine.get_page(url)
def parse_page(text: str) -> GeneralInfo:
    result: GeneralInfo = {}
    matches = re.findall(r'<table\sclass="tbl-chitiet">(.*?)</table>', text, re.DOTALL)
    match = matches[0]
    titles: list[str] = re.findall(r'<td\sclass="td-lable">(.*?)</td>', match, re.DOTALL)
    values: list[str] = re.findall(r'<td>(.*?)</td>', match, re.DOTALL)
    titles.extend(re.findall(r'<td\sclass="td-lable"\sstyle="font-style:italic;">(.*?)</td>', match, re.DOTALL))
    values.extend(re.findall(r'<td\sstyle="font-style:italic;">(.*?)</td>', match, re.DOTALL))
    for index, key  in enumerate(titles):
        key = key.replace("- ", "")
        value = values[index]
        result[key] = value
    website = result["Website"]
    if website:
        website = re.findall(r">(.*?)</a>", website)[0]
    result["Website"] = website
    return result
async def download():
    engine = CrawlEngine(16)
    await engine.start()
    ids = await get_ids()
    jobs = []
    for id in ids:
        url = URL.format(id=id)
        job = engine.get_page(url)
        jobs.append(job)
    texts = await asyncio.gather(*jobs)
    await engine.stop()
    data: list[GeneralInfo] = []
    for text in texts:
        data.append(parse_page(text))
    with open("info.csv", 'w', newline='\n', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=list(get_args(TITLES)))
        writer.writeheader()
        writer.writerows(data)
if __name__ == "__main__":
    asyncio.run(download())