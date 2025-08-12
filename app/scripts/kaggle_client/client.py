from aiohttp import ClientSession, ClientTimeout
import asyncio
import queue
import threading
import copy
from typing import TypedDict
from typing import cast
from .model_schema import *

# class TaskInfo(TypedDict):
#     scheduled: bool
#     completed: bool
#     canceled: bool
#     info: JobInfo
#     result: JobResult
#     ref: asyncio.Task

class ClientSide:
    def __init__(self,
        client_info: ClientInfo,
        url: str,
        success_url: str,
        failed_url: str,
        poll: float = 1
    ):
        self.client_info = client_info
        self.url = url
        self.success_url = success_url
        self.failed_url = failed_url
        self._input_queue: list[JobInfo] = []
        self.timeout = ClientTimeout(5)
        self.poll = poll
    def get_client_info(self) -> ClientInfo:
        return self.client_info
    async def start(self):
        if hasattr(self, "worker_task"):
            raise Exception(f"Aldready started")
        self.session = ClientSession()
        self.worker_task = asyncio.create_task(self.__worker())
    async def __worker(self):
        try:
            print(f"Client started")
            while True:
                try:
                    has_request = True
                    # Get request
                    while has_request: # Get till None
                        has_request = await self._process_input()                        
                except ConnectionError as e:
                    print(f"Connection error: {e}")
                await asyncio.sleep(self.poll)
        except asyncio.CancelledError:
            print(f"Client stopped")
    async def _process_input(self):
        # Return True when success retrieve a job
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
                    self._input_queue.append(job_info)
                    return True
            except Exception as e:
                print(f"Error while reading response: {e}")
        else:
            print(f"Error when get info: {response.status} | {await response.text()}")
    async def get_job(self) -> list[JobInfo]:
        jobs = []
        for job in self._input_queue:
            jobs.append(job)
        self._input_queue.clear()
        return jobs
    async def submit_result(self, result: JobResult):
        if result["success"]:
            response_data = ResponseData(
                client=self.get_client_info(),
                job_id=result["id"],
                payload=cast(ModelOutput, result["data"])
            )
            await self._send_result(response_data)
        else:
            error_data = ErrorData(
                client=self.get_client_info(),
                job_id=result["id"],
                error=cast(str, result["data"])
            )
            await self._send_error(error_data)
    async def _send_result(self, data: ResponseData):
        response = await self.session.post(self.success_url, json=data)
        if response.status != 200:
            print(f"Error when send back result: {response.status} | {await response.text()}")
    async def _send_error(self, data: ErrorData):
        response = await self.session.post(self.failed_url, json=data)
        if response.status != 200:
            print(f"Error when send back result: {response.status} | {await response.text()}")
    async def stop(self):
        if not hasattr(self, "worker_task"):
            raise Exception(f"Not started")
        self.worker_task.cancel()

        await self.session.close()
        delattr(self, "worker_task")