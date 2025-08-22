from aiohttp import ClientSession, ClientTimeout
import asyncio
import queue
import threading
import copy
from typing import TypedDict
from typing import cast
from .model_schema import *

class ClientSide:
    worker_thread: threading.Thread
    active = True
    _running = True
    client_info: ClientInfo
    _input_queue: queue.Queue[JobInfo] = queue.Queue()
    _url: str 
    _success_url: str
    _failed_url: str
    _poll: float 
    _timeout: ClientTimeout
    def __init__(self):
        raise NotImplementedError("ClientSide does not support instance")
    @classmethod
    def start(cls, 
        client_info: ClientInfo,
        url: str,
        success_url: str,
        failed_url: str,
        poll: float,
        timeout: float):
        # Main thread call
        if hasattr(ClientSide, "worker_thread"):
            print(f"Client aldready started")
        ClientSide._running = True
        ClientSide.active = True
        ClientSide.client_info = client_info
        ClientSide._url = url
        ClientSide._success_url = success_url
        ClientSide._failed_url = failed_url
        ClientSide._poll = poll
        ClientSide._timeout = ClientTimeout(timeout)
        ClientSide.worker_thread = threading.Thread(target=cls.__worker_job, daemon=True)
        ClientSide.worker_thread.start()
    @classmethod
    def __worker_job(cls):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(cls.__worker())
    @classmethod
    async def __worker(cls):
        print(f"Client started")
        while ClientSide._running:
            if ClientSide.active:
                try:
                    has_request = True
                    # Get request
                    while has_request: # Get till None
                        has_request = await cls._process_input()                        
                except ConnectionError as e:
                    print(f"Connection error: {e}")
            await asyncio.sleep(cls._poll)
    @classmethod
    async def _process_input(cls):
        # Return True when success retrieve a job
        try:
            async with ClientSession() as session:
                async with session.post(cls._url, json=cls.client_info, timeout=cls._timeout) as response:
                    if response.ok:
                        try:
                            data: RequestData = await response.json()
                            if "job_id" in data and data["job_id"] != None and data["payload"] != None:
                                job_info = JobInfo({
                                    "data": data["payload"],
                                    "id": data["job_id"]
                                })
                                cls._input_queue.put(job_info)
                                return True
                        except Exception as e:
                            print(f"Error while reading response: {e}")
                    else:
                        print(f"Error when get info: {response.status} | {await response.text()}")
        except Exception as e:
            print(f"Connection error: {e}")
            return
    @classmethod
    async def get_job(cls) -> list[JobInfo]:
        # Main thread call
        jobs = []
        while not cls._input_queue.empty():
            jobs.append(cls._input_queue.get())
        return jobs
    @classmethod
    async def submit_result(cls, result: JobResult):
        # Main thread call
        if result["success"]:
            response_data = ResponseData(
                client=cls.client_info,
                job_id=result["id"],
                payload=cast(ModelOutput, result["data"])
            )
            await cls._send_result(response_data)
        else:
            error_data = ErrorData(
                client=cls.client_info,
                job_id=result["id"],
                error=cast(str, result["data"])
            )
            await cls._send_error(error_data)
    @classmethod
    async def _send_result(cls, data: ResponseData):
        async with ClientSession() as session:
            async with session.post(cls._success_url, json=data) as response:
                if not response.ok:
                    print(f"Error when send back result: {response.status} | {await response.text()}")
    @classmethod
    async def _send_error(cls, data: ErrorData):
        async with ClientSession() as session:
            async with session.post(cls._failed_url, json=data) as response:
                if not response.ok:
                    print(f"Error when send back result: {response.status} | {await response.text()}")
    @classmethod
    async def stop(cls, timeout: float = 10):
        # Main thread call
        if not hasattr(cls, "worker_thread"):
            raise Exception(f"Not started")
        cls.worker_thread.join(timeout)
        attrs = [
            "worker_task", "client_info", "_url", "_success_url", "_failed_url", "_poll", "_timeout", "client_info"
        ]
        for attr_name in attrs:
            delattr(ClientSide, attr_name)