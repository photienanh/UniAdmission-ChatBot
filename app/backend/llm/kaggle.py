import aiohttp
from typing import AsyncGenerator, TypedDict
import time

from config import KAGGLE_SERVER_TIMEOUT
from core.types import GenerationParams, ModelInfo, ModelPreOutput, KagglePreInferenceResponse, KaggleServerInfo, KaggleRequest
from .schema import ServerStatus

class DomainCountDict(TypedDict):
    domain: str
    count: int

class KaggleManager:
    _servers: list[ServerStatus] = []
    @classmethod
    async def get_available_domain(cls, model_id: str) -> str | None:
        """Find best suitable domain to run this model with `model_id`"""
        # May have timelag because synchronize between servers, kaggle should send response when received server request
        available_domains: list[DomainCountDict] = []
        active_domains: list[DomainCountDict] = []
        scheduled_domains: list[DomainCountDict] = []
        now = time.time()
        to_be_remove = []
        for server in cls._servers:
            alive = server["timestamp"] - now <= KAGGLE_SERVER_TIMEOUT # Check if timeout
            if not alive:
                alive = cls._check_connection(server) # Reconnect
            if not alive:
                to_be_remove.append(server)
            if alive:
                for model in server["info"]["models"]:
                    if model["id"] == model_id:
                        if model["active"]:
                            active_domains.append({
                                "domain": server["info"]["domain"],
                                "count": model["active_count"]
                            })
                            break
                        elif model["scheduled"]:
                            scheduled_domains.append({
                                "domain": server["info"]["domain"],
                                "count": model["scheduled_count"]
                            })
                        else:
                            available_domains.append({
                                "domain": server["info"]["domain"],
                                "count": 0
                            })
        for server in to_be_remove:
            cls._servers.remove(server)
        if len(available_domains) > 0:
            # Send to server where have more jobs => To prevent switching model
            max_count = available_domains[0]["count"]
            target_domain = available_domains[0]["domain"]
            for info in available_domains:
                if info["count"] > max_count:
                    max_count = info["count"]
            return target_domain
        if len(scheduled_domains) > 0:
            # Model in this is not activated, only scheduled
            # Send to server where have more jobs => To prevent switching model
            max_count = available_domains[0]["count"]
            target_domain = available_domains[0]["domain"]
            for info in available_domains:
                if info["count"] > min_count:
                    min_count = info["count"]
            return target_domain
        if len(available_domains) > 0:
            return available_domains[0]["domain"]
    @classmethod
    def get_models(cls) -> list[ModelInfo]:
        result: list[ModelInfo] = []
        for server in cls._servers:
            result.extend(server["info"]["models"])
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
            domain = await cls.get_available_domain(model_id)
            if domain != None:
                url = f"{domain}/pre_inference"
                async with ss.post(url=url, json=request) as response:
                    if response.ok:
                        result: KagglePreInferenceResponse = await response.json() #TODO: Handle error
                        cls.update_server(result["info"])
                        return domain, result["pre_output"]
                    else:
                        print(f"[Kaggle Client] Errr {domain}: {response.status}: {await response.text()}")
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
            url = f"{server["info"]["domain"]}/info"
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
            