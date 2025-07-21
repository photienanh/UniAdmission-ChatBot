import os
from utility import parse_text
import asyncio
import aiofiles
from typing import NamedTuple
import threading

raw_base_path = "data/school_raw"
parsed_base_path = "data/parsed_x"
empty_log_path = "data/parsed_x/_empty_{tid}.txt"
MIN_THRESHOLD = 2000
if not os.path.exists(parsed_base_path): os.makedirs(parsed_base_path)

def processs_text(text: str) -> str:
    lines = text.splitlines()
    valid_lines: list[str] = []
    for line in lines:
        line = line.strip()
        if line != "":
            valid_lines.append(line)
    return "\n".join(valid_lines)
class JobInfo(NamedTuple):
    input_path: str
    output_path: str
def split(lst: list, n: int):
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m) : (i+1)*k + min(i+1, m)] for i in range(n)]
async def task(tid: int, index: int, semaphore: asyncio.Semaphore, info: JobInfo, log_path: str):
    async with semaphore:
        try:
            # print(f"Start {info.input_path}")
            async with aiofiles.open(info.input_path, 'r', encoding='utf-8') as file:
                text = await file.read()
            parsed_text = parse_text(text)
            processed_text = processs_text(parsed_text)
            if len(processed_text) < MIN_THRESHOLD:
                async with aiofiles.open(log_path, 'a', encoding='utf-8') as file:
                    await file.write(f"{len(processed_text)}|{info.input_path}\n")
            else:
                async with aiofiles.open(info.output_path, 'w', encoding='utf-8') as file:
                    await file.write(processed_text)
        except:
            pass
    if index % 100 == 0:
        print(f"Completed {tid}:{index}")
def thread_task(tid: int, thread_job_infos: list[JobInfo], log_path: str):
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    thread_jobs = []
    semaphore = asyncio.Semaphore(64)
    async def run_thread_jobs():
        for info in thread_job_infos:
            job = task(tid, len(thread_jobs), semaphore, info, log_path)
            thread_jobs.append(asyncio.create_task(job))
        await asyncio.gather(*thread_jobs)
    asyncio.run(run_thread_jobs())
def run_parser():
    num_threads = 4 # Cha'y ma'y :))
    job_infos = []
    for folder_name in os.listdir(raw_base_path):
        
        folder_path = os.path.join(raw_base_path, folder_name)
        parsed_folder = os.path.join(parsed_base_path, folder_name)
        if not os.path.exists(parsed_folder): os.mkdir(parsed_folder)
        for file_name in os.listdir(folder_path):
            raw_path = os.path.join(folder_path, file_name)
            parsed_path = os.path.join(parsed_folder, file_name.replace(".html", ".txt"))
            job_infos.append(JobInfo(raw_path, parsed_path))
    splitted_job_infoss = split(job_infos, num_threads)
    threads: list[threading.Thread] = []
    for index in range(num_threads):
        thread = threading.Thread(target=thread_task, args=[index, splitted_job_infoss[index], empty_log_path.format(tid=index)])
        threads.append(thread)
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    run_parser()