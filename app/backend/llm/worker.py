import aiohttp
from typing import TypedDict
import time
import asyncio
from datetime import datetime, timezone

from config import WORKER_TIMEOUT, WORKER_MAX_RETRY, WORKER_REQUEST_TIMEOUT, WORKER_WAIT_TIMEOUT, WORKER_RETRY_DELAY
from core.types import GenerationParams, ModelInfo, ModelPreOutput, WorkerPreInferenceResponse, WorkerServerInfo, WorkerChatRequest, ChatMessage

class WorkerStatus(TypedDict):
    info: WorkerServerInfo
    timestamp: float
class WorkerManager:
    """Need to hold worker domains, so we add a little cache. It can't be fully stateless."""
    _servers: list[WorkerStatus] = []
    _timeout = aiohttp.ClientTimeout(
        total=WORKER_WAIT_TIMEOUT + WORKER_REQUEST_TIMEOUT,
        connect=WORKER_REQUEST_TIMEOUT, 
        sock_connect=WORKER_WAIT_TIMEOUT, 
        sock_read=WORKER_WAIT_TIMEOUT
    )
    @classmethod
    async def get_available_worker(cls, model_id: str) -> WorkerStatus | None:
        """Find FIRST available domain to run this model with `model_id`"""
        to_be_remove = []
        result: WorkerStatus | None = None
        for server in cls._servers:
            if await cls._check_alive(server):
                for model in server["info"]["models"]:
                    if model["id"] == model_id and result == None:
                        result = server
            else:
                to_be_remove.append(server)
        for server in to_be_remove:
            cls._servers.remove(server)
            print(f"[Kaggle] Disconnect: {server['info']['domain']}")
        return result
    @classmethod
    async def get_models(cls) -> list[ModelInfo]:
        """Get all domain models"""
        to_be_remove: list[WorkerStatus] = []
        result: list[ModelInfo] = []
        model_ids = set([])
        for server in cls._servers:
            if await cls._check_alive(server):
                for model in server["info"]["models"]:
                    if model["id"] not in model_ids:
                        model_ids.add(model["id"])
                        result.append(model)
            else:
                to_be_remove.append(server)
        for server in to_be_remove:
            cls._servers.remove(server)
            print(f"[Kaggle] Disconnect: {server['info']['domain']}")
        return result
    @classmethod
    async def pre_inference(cls, user_id: str,  session_id: str, text: str, history: list[ChatMessage], params: GenerationParams) -> ModelPreOutput | None:
        """
        Pre inference model to get `ModelPreOutput`.\n
        Return `None` when does not find any available server or when error occur.
        """
        request: WorkerChatRequest = {
            "text": text,
            "params": params,
            "history": history,
            "forward_kwargs": {
                "session_id": session_id,
                "user_id": user_id,
                "user_text": text,
                "user_timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        model_id = params["model_id"]
        async with aiohttp.ClientSession(timeout=cls._timeout) as ss:
            server = await cls.get_available_worker(model_id)
            if server is None: return
            retry = 0
            while retry <= WORKER_MAX_RETRY:
                if server != None:
                    url = f"{server['info']['domain']}/pre_inference"
                    # Try to connect
                    try:
                        if await cls._check_alive(server): # Precheck to avoid wait for closed server
                            async with ss.post(url=url, json=request) as response:
                                if response.ok:
                                    result: WorkerPreInferenceResponse = await response.json() #TODO: Handle error
                                    cls.update_worker(result["info"])
                                    return result["pre_output"]
                                else:
                                    print(await response.text())
                                # 404 not found, error, ...
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        pass
                # Failed to pre inference, then we:
                await asyncio.sleep(WORKER_RETRY_DELAY) # Wait for death server to timeout
                if server != None:
                    await cls._cleanup_if_dead(server) # Clean death server
                server = await cls.get_available_worker(model_id)
                retry += 1
            # When server is dead or max retry exceed
            if server != None:
                await cls._cleanup_if_dead(server)
    @classmethod
    async def _check_alive(cls, server: WorkerStatus) -> bool:
        """Check if server is alive (within timeout). If timeout, try reconnect."""
        alive = time.time() - server["timestamp"] <= WORKER_TIMEOUT # Check if timeout
        if not alive:
            alive = await cls._check_connection(server) # Reconnect
        return alive
    @classmethod
    async def _check_connection(cls, server: WorkerStatus) -> bool:
        try:
            async with aiohttp.ClientSession(timeout=cls._timeout) as ss:
                url = f"{server['info']['domain']}/info"
                async with ss.get(url=url) as response:
                    if response.ok:
                        info: WorkerServerInfo = await response.json()
                        server["info"] = info
                        server["timestamp"] = time.time()
                        return True
            return False
        except aiohttp.ClientConnectorError:
            # When server is closed or not exist
            return False
        except aiohttp.ConnectionTimeoutError:
            # Server is freeze
            return False
    @classmethod
    async def _cleanup_if_dead(cls, server: WorkerStatus):
        """Try to cleanup server if it's dead"""
        if not await cls._check_connection(server):
            if server in cls._servers:
                cls._servers.remove(server)
                print(f"[Kaggle] Disconnect: {server['info']['domain']}")
    @classmethod
    def update_worker(cls, info: WorkerServerInfo):
        """Register/Update worker info"""
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

            