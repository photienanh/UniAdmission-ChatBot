import aiohttp
from typing import AsyncGenerator, TypedDict
import time
import asyncio

from config import KAGGLE_SERVER_TIMEOUT, KAGGLE_MAX_RETRY, KAGGLE_RETRY_DELAY
from core.types import GenerationParams, ModelInfo, ModelPreOutput, KagglePreInferenceResponse, KaggleServerInfo, KaggleRequest
from .schema import ServerStatus

class ServerCountDict(TypedDict):
    server: ServerStatus
    count: int

class KaggleManager:
    _servers: list[ServerStatus] = []
    @classmethod
    async def get_available_server(cls, model_id: str) -> ServerStatus | None:
        """Find best suitable domain to run this model with `model_id`"""
        # May have timelag because synchronize between servers, kaggle should send response when received server request
        available_servers: list[ServerCountDict] = []
        active_servers: list[ServerCountDict] = []
        scheduled_servers: list[ServerCountDict] = []
        now = time.time()
        to_be_remove = []
        for server in cls._servers:
            alive = now - server["timestamp"] <= KAGGLE_SERVER_TIMEOUT # Check if timeout
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
        to_be_remove: list[ServerStatus] = []
        now = time.time()
        result: list[ModelInfo] = []
        model_ids = set([])
        for server in cls._servers:
            alive = now - server["timestamp"]<= KAGGLE_SERVER_TIMEOUT # Check if timeout
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
    async def pre_inference(cls, stream_id: str, text: str, model_id: str, params: GenerationParams) -> tuple[str, ModelPreOutput] | None:
        """
        Pre inference model to get `domain` and `ModelPreOutput`.\n
        Return `None` when does not find any available server or when error occur.
        """
        request: KaggleRequest = {
            "stream_id": stream_id,
            "model_id": model_id,
            "text": text,
            "params": params
        }
        async with aiohttp.ClientSession() as ss:
            server = await cls.get_available_server(model_id)
            retry = 0
            while retry < KAGGLE_MAX_RETRY:
                if server != None:
                    url = f"{server['info']['domain']}/pre_inference"
                    # Try to connect
                    try:
                        async with ss.post(url=url, json=request) as response:
                            if response.ok:
                                result: KagglePreInferenceResponse = await response.json() #TODO: Handle error
                                cls.update_server(result["info"])
                                return server["info"]["domain"], result["pre_output"]
                            # 404 not found, error, ...
                    except:
                        pass
                    await asyncio.sleep(KAGGLE_RETRY_DELAY) # Wait for death server to timeout
                    await cls.get_models() # Clean death server
                    server = await cls.get_available_server(model_id)
                    retry += 1
                   
    @classmethod
    async def inference(cls, domain: str, job_id: str) -> AsyncGenerator[str, None]:
        """
        Need this to store result in server.\n
        Otherwise user redirect would be better.
        """
        async with aiohttp.ClientSession() as ss:
            url = f"{domain}/inference/{job_id}"
            async with ss.post(url=url) as response:
                if response.ok:
                    async for chunk in response.content.iter_any():
                        yield chunk.decode("utf-8")
    @classmethod
    async def _check_connection(cls, server: ServerStatus) -> bool:
        async with aiohttp.ClientSession() as ss:
            url = f"{server['info']['domain']}/info"
            async with ss.get(url=url) as response:
                if response.ok:
                    info: KaggleServerInfo = await response.json()
                    server["info"] = info
                    server["timestamp"] = time.time()
                    return True
        return False
    @classmethod
    def update_server(cls, info: KaggleServerInfo):
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
        print(f"[Kaggle] New connection {info['domain']}")

            