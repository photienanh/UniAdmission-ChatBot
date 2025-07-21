import asyncio
import re
from utility import CrawlEngine
import json
import os

URL = "https://moet.gov.vn/cosogiaoduc/Pages/danh-sach.aspx?search=1&field=Title&asc=True&Page={index}"

async def download():
    engine = CrawlEngine(8)
    limit = 100
    ids: list[int] = []
    await engine.start()
    page_index = 1
    while True:
        jobs = []
        for offset in range(engine.limit):
            # print(f"Start job {page_index+offset}")
            url = URL.format(index=page_index+offset)
            job = engine.get_page(url)
            jobs.append(job)
        texts = await asyncio.gather(*jobs) # Schedule n job
        matches = re.findall(r'<a\shref="\?ItemID=(\d+)">', " ".join(texts), re.DOTALL) # Find id in batch
        batch_ids = [int(match) for match in matches]
        page_index += engine.limit
        if len(batch_ids) > 0: # Stop if batch has no id
            ids.extend(batch_ids)
        else:
            print(f"Stop at {page_index-1}")
            break
        if page_index > limit: # Stop if reach limit
            print(f"Stop at {page_index}")
            break        
    await engine.stop()
    with open("data/info/ids.txt", 'w') as file:
        file.write(json.dumps(ids))
    return ids


async def get_ids() -> list[int]:
    if not os.path.exists("data/info/ids.txt"):
        return await download()
    else:
        with open("data/info/ids.txt", 'r') as file:
            return json.loads(file.read())

if __name__ == "__main__":
    asyncio.run(get_ids())
