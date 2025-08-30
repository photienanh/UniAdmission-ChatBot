import aiohttp
from typing import TypedDict
import time
import asyncio
from datetime import datetime, timezone

from config import WORKER_TIMEOUT, WORKER_MAX_RETRY, WORKER_REQUEST_TIMEOUT
from core.types import GenerationParams, ModelInfo, ModelPreOutput, WorkerPreInferenceResponse, WorkerServerInfo, WorkerChatRequest, ChatMessage
from .schema import WorkerStatus

class WorkerCountDict(TypedDict):
    server: WorkerStatus
    count: int
class WorkerManager:
    _servers: list[WorkerStatus] = []
    _timeout = aiohttp.ClientTimeout(WORKER_REQUEST_TIMEOUT)
    @classmethod
    async def get_available_worker(cls, model_id: str) -> WorkerStatus | None:
        """Find best suitable domain to run this model with `model_id`"""
        # May have timelag because synchronize between servers, kaggle should send response when received server request
        available_servers: list[WorkerCountDict] = []
        active_servers: list[WorkerCountDict] = []
        scheduled_servers: list[WorkerCountDict] = []
        now = time.time()
        to_be_remove = []
        for server in cls._servers:
            alive = now - server["timestamp"] <= WORKER_TIMEOUT # Check if timeout
            if not alive:
                alive = await cls._check_connection(server) # Reconnect
            if not alive:
                to_be_remove.append(server)
            if alive:
                for model in server["info"]["models"]:
                    if model["id"] == model_id:
                        if model["active"]:
                            active_servers.append({
                                "server": server,
                                "count": model["active_count"]
                            })
                            break
                        elif model["scheduled"]:
                            scheduled_servers.append({
                                "server": server,
                                "count": model["scheduled_count"]
                            })
                        else:
                            available_servers.append({
                                "server": server,
                                "count": 0
                            })
        for server in to_be_remove:
            cls._servers.remove(server)
            print(f"[Kaggle] Disconnect: {server['info']['domain']}")
        if len(active_servers) > 0:
            # Send to server where have more jobs => To prevent switching model
            max_count = active_servers[0]["count"]
            target_server = active_servers[0]["server"]
            for info in active_servers:
                if info["count"] > max_count:
                    max_count = info["count"]
                    target_server = info["server"]
            return target_server
        if len(scheduled_servers) > 0:
            # Model in this is not activated, only scheduled
            # Send to server where have more jobs => To prevent switching model
            max_count = scheduled_servers[0]["count"]
            target_server = scheduled_servers[0]["server"]
            for info in scheduled_servers:
                if info["count"] > min_count:
                    min_count = info["count"]
            return target_server
        if len(available_servers) > 0:
            return available_servers[0]["server"]
    @classmethod
    async def get_models(cls) -> list[ModelInfo]:
        to_be_remove: list[WorkerStatus] = []
        now = time.time()
        result: list[ModelInfo] = []
        model_ids = set([])
        for server in cls._servers:
            alive = now - server["timestamp"] <= WORKER_TIMEOUT # Check if timeout
            if not alive:
                alive = await cls._check_connection(server) # Reconnect
            if not alive:
                to_be_remove.append(server)
            for model in server["info"]["models"]:
                if model["id"] not in model_ids:
                    model_ids.add(model["id"])
                    result.append(model)
        for server in to_be_remove:
            cls._servers.remove(server)
            print(f"[Kaggle] Disconnect: {server['info']['domain']}")
        return result
    @classmethod
    async def pre_inference(cls, user_id: str, stream_id: str, text: str, model_id: str, history: list[ChatMessage], params: GenerationParams) -> ModelPreOutput | None:
        """
        Pre inference model to get `domain` and `ModelPreOutput`.\n
        Return `None` when does not find any available server or when error occur.
        """
        request: WorkerChatRequest = {
            "stream_id": stream_id,
            "model_id": model_id,
            "text": text,
            "params": params,
            "history": history,
            "forward_kwargs": {
                "stream_id": stream_id,
                "user_id": user_id,
                "user_text": text,
                "user_timestamp": datetime.now(timezone.utc)
            }
        }
        async with aiohttp.ClientSession(timeout=cls._timeout) as ss:
            server = await cls.get_available_worker(model_id)
            if server is None: return
            retry = 0
            while retry < WORKER_MAX_RETRY:
                if server != None:
                    url = f"{server['info']['domain']}/pre_inference"
                    # Try to connect
                    try:
                        async with ss.post(url=url, json=request) as response:
                            if response.ok:
                                result: WorkerPreInferenceResponse = await response.json() #TODO: Handle error
                                cls.update_worker(result["info"])
                                return result["pre_output"]
                            # 404 not found, error, ...
                    except:
                        pass
                    await asyncio.sleep(WORKER_MAX_RETRY) # Wait for death server to timeout
                    await cls.get_models() # Clean death server
                    server = await cls.get_available_worker(model_id)
                    retry += 1
    @classmethod
    async def _check_connection(cls, server: WorkerStatus) -> bool:
        async with aiohttp.ClientSession(timeout=cls._timeout) as ss:
            url = f"{server['info']['domain']}/info"
            async with ss.get(url=url) as response:
                if response.ok:
                    info: WorkerServerInfo = await response.json()
                    server["info"] = info
                    server["timestamp"] = time.time()
                    return True
        return False
    @classmethod
    def update_worker(cls, info: WorkerServerInfo):
        now = time.time()
        for server in cls._servers:
            if server["info"]["domain"] == info["domain"]:
                server["info"] = info
                server["timestamp"] = now
                return
        cls._servers.append({
            "info": info,
            "timestamp": now
        })
        print(f"[Kaggle] New connection: {info['domain']}")

            