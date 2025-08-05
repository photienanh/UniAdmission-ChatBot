from aiohttp import ClientSession, ClientTimeout
import asyncio
import queue
import threading
import copy
from typing import TypedDict, Optional, Literal, cast
from .model_schema import *

class ClientSide:
    def __init__(self,
        client_info: ClientInfo,
        url: str,
        success_url: str,
        failed_url: str,
        poll: float = 0.5
    ):
        self.client_info = copy.deepcopy(client_info)
        self.poll = poll
        self.url = url
        self.success_url = success_url
        self.failed_url = failed_url
        self.input_queue = queue.Queue[JobInfo]()
        self.output_queue = queue.Queue[JobResult]()
        self.timeout = ClientTimeout(5)
        self.running = True
    def get_client_info(self) -> ClientInfo:
        return self.client_info
    async def start(self):
        if hasattr(self, "task"):
            raise Exception(f"Aldready started")
        self.session = ClientSession()
        await self.worker()
    async def worker(self):
        while self.running:
            try:
                # Get request
                await self.process_input()
                # Sendback response
                await self.process_output()
            except ConnectionError as e:
                print(f"Connection error: {e}")
            await asyncio.sleep(self.poll)
    async def process_input(self):
        try:
            response = await self.session.post(self.url, json=self.get_client_info(), timeout=self.timeout)
        except Exception as e:
            print(f"Connection error: {e}")
            return
        if response.status == 200:
            try:
                data: RequestData = await response.json()
                if "job_id" in data and data["job_id"] != None and data["payload"] != None:
                    job_info = JobInfo({
                        "data": data["payload"],
                        "id": data["job_id"]
                    })
                    self.input_queue.put(job_info)
            except Exception as e:
                print(f"Error while reading response: {e}")
        else:
            print(f"Error when get info: {response.status} | {await response.text()}")
    async def process_output(self):
        if self.output_queue.qsize() > 0:
            result = self.output_queue.get()
            if result["success"]:
                response_data = ResponseData(
                    client=self.get_client_info(),
                    job_id=result["id"],
                    payload=cast(ModelOutput, result["data"])
                )
                await self.send_result(response_data)
            else:
                error_data = ErrorData(
                    client=self.get_client_info(),
                    job_id=result["id"],
                    error=cast(str, result["data"])
                )
                await self.send_error(error_data)
    async def send_result(self, data: ResponseData):
        response = await self.session.post(self.success_url, json=data)
        if response.status != 200:
            print(f"Error when send back result: {response.status} | {await response.text()}")
    async def send_error(self, data: ErrorData):
        response = await self.session.post(self.failed_url, json=data)
        if response.status != 200:
            print(f"Error when send back result: {response.status} | {await response.text()}")
    async def stop(self):
        if not hasattr(self, "task"):
            raise Exception(f"Not started")
        self.running = False
        await self.session.close()
        delattr(self, "task")
        
    @classmethod
    def run_as_service(cls, client_info: ClientInfo, url: str, success_url: str, failed_url: str):
        ref: ClientSide = None #type:ignore
        def thread_job():
            nonlocal ref
            instance = ClientSide(client_info, url, success_url, failed_url)
            ref = instance
            async def job():
                await instance.start()
            asyncio.run(job())
        thread = threading.Thread(target=thread_job)
        thread.start()
        return ref.input_queue, ref.output_queue, thread