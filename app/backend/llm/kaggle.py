import aiohttp
from typing import AsyncGenerator, TypedDict
import time
import asyncio

from config import KAGGLE_SERVER_TIMEOUT, KAGGLE_MAX_RETRY, KAGGLE_RETRY_DELAY
from core.types import GenerationParams, ModelInfo, ModelPreOutput, KagglePreInferenceResponse, KaggleServerInfo, KaggleRequest, ChatMessage
from .schema import ServerStatus

# Kiểu dữ liệu phụ: lưu server + số lượng job
class ServerCountDict(TypedDict):
    server: ServerStatus
    count: int


class KaggleManager:
    # Danh sách server Kaggle mà hệ thống biết (đã kết nối / ping được)
    _servers: list[ServerStatus] = []

    @classmethod
    async def get_available_server(cls, model_id: str) -> ServerStatus | None:
        """
        Chọn server phù hợp nhất để chạy model với `model_id`.
        Ưu tiên: active_servers > scheduled_servers > available_servers.
        """
        available_servers: list[ServerCountDict] = []
        active_servers: list[ServerCountDict] = []
        scheduled_servers: list[ServerCountDict] = []
        now = time.time()
        to_be_remove = []

        # Duyệt qua tất cả server đã lưu
        for server in cls._servers:
            # Check server còn "sống" không (theo timestamp)
            alive = now - server["timestamp"] <= KAGGLE_SERVER_TIMEOUT
            if not alive:
                # Nếu timeout thì thử reconnect
                alive = await cls._check_connection(server)
            if not alive:
                # Nếu vẫn chết → đưa vào danh sách xóa
                to_be_remove.append(server)

            if alive:
                # Check server có hỗ trợ model này không
                for model in server["info"]["models"]:
                    if model["id"] == model_id:
                        if model["active"]:
                            # Model đang chạy → ưu tiên server có nhiều active job nhất
                            active_servers.append({
                                "server": server,
                                "count": model["active_count"]
                            })
                            break
                        elif model["scheduled"]:
                            # Model đã scheduled nhưng chưa active
                            scheduled_servers.append({
                                "server": server,
                                "count": model["scheduled_count"]
                            })
                        else:
                            # Model có trong server nhưng chưa chạy gì
                            available_servers.append({
                                "server": server,
                                "count": 0
                            })

        # Xóa server chết khỏi danh sách
        for server in to_be_remove:
            cls._servers.remove(server)
            print(f"[Kaggle] Disconnect: {server['info']['domain']}")

        # Ưu tiên chọn server có nhiều job nhất (để giữ model "warm")
        if len(active_servers) > 0:
            max_count = active_servers[0]["count"]
            target_server = active_servers[0]["server"]
            for info in active_servers:
                if info["count"] > max_count:
                    max_count = info["count"]
                    target_server = info["server"]
            return target_server

        if len(scheduled_servers) > 0:
            max_count = scheduled_servers[0]["count"]
            target_server = scheduled_servers[0]["server"]
            for info in scheduled_servers:
                if info["count"] > max_count:
                    max_count = info["count"]
                    target_server = info["server"]
            return target_server

        if len(available_servers) > 0:
            return available_servers[0]["server"]


    @classmethod
    async def get_models(cls) -> list[ModelInfo]:
        """
        Lấy danh sách models từ tất cả server hiện tại.
        Đồng thời cleanup server chết.
        """
        to_be_remove: list[ServerStatus] = []
        now = time.time()
        result: list[ModelInfo] = []
        model_ids = set([])

        for server in cls._servers:
            alive = now - server["timestamp"] <= KAGGLE_SERVER_TIMEOUT
            if not alive:
                alive = await cls._check_connection(server)
            if not alive:
                to_be_remove.append(server)

            # Gộp models từ server, tránh trùng id
            for model in server["info"]["models"]:
                if model["id"] not in model_ids:
                    model_ids.add(model["id"])
                    result.append(model)

        # Cleanup
        for server in to_be_remove:
            cls._servers.remove(server)
            print(f"[Kaggle] Disconnect: {server['info']['domain']}")

        return result


    @classmethod
    async def pre_inference(
        cls, stream_id: str, question: str, model_id: str,
        params: GenerationParams, conversation_history: list[ChatMessage],
        vector_sources: list = None, web_keywords: list = None
    ) -> tuple[str, ModelPreOutput] | None:
        """
        Gửi request pre_inference đến server Kaggle.
        vector_sources: sources đã search từ app/ level
        web_keywords: keywords để kaggle search nếu không có vector_sources
        """
        # Chuẩn bị request gửi tới server
        request: KaggleRequest = {
            "stream_id": stream_id,
            "model_id": model_id,
            "question": question,
            "params": params,
            "history": conversation_history
        }
        
        # Thêm vector_sources vào request nếu có
        print(f"[KaggleManager] vector_sources received: {vector_sources}")
        print(f"[KaggleManager] vector_sources check: {bool(vector_sources)}")
        if vector_sources:
            request["vector_sources"] = vector_sources
            print(f"[KaggleManager] Added {len(vector_sources)} vector sources to request")
        else:
            print(f"[KaggleManager] No vector sources to add")
        
        # Thêm web_keywords vào request nếu có (khi app search fail)
        if web_keywords:
            request["web_search_keywords"] = web_keywords

        # Tạo session HTTP
        async with aiohttp.ClientSession() as ss:
            server = await cls.get_available_server(model_id)
            retry = 0
            while retry < KAGGLE_MAX_RETRY:
                if server != None:
                    url = f"{server['info']['domain']}/pre_inference"
                    try:
                        # Gửi request tới server
                        async with ss.post(url=url, json=request) as response:
                            if response.ok:
                                # Lấy kết quả pre_inference từ server
                                result: KagglePreInferenceResponse = await response.json()
                                cls.update_server(result["info"])

                                # Lưu chỉ web_sources
                                pre_output = result["pre_output"]
                                web_sources = pre_output.get("web_sources", [])
                                cls.store_sources(stream_id, web_sources)

                                return server["info"]["domain"], result["pre_output"]
                            else:
                                response_text = await response.text()
                                print(f"[KaggleManager] Request failed with status {response.status}: {response_text}")

                    except Exception as e:
                        # Nếu lỗi kết nối thì retry
                        print(f"[KaggleManager] Request exception: {e}")
                        pass

                    # Đợi cho server timeout rồi thử server khác
                    await asyncio.sleep(KAGGLE_RETRY_DELAY)
                    await cls.get_models()  # Cleanup server chết
                    server = await cls.get_available_server(model_id)
                    retry += 1
                else:
                    print(f"[KaggleManager] No available server found for model: {model_id}")
                    break

        print(f"[KaggleManager] All retries exhausted, returning None")
        return None


    @classmethod
    async def inference(cls, domain: str, job_id: str) -> AsyncGenerator[str, None]:
        """
        Gửi request inference tới server Kaggle và stream output về.
        """
        async with aiohttp.ClientSession() as ss:
            url = f"{domain}/inference/{job_id}"
            async with ss.post(url=url) as response:
                if response.ok:
                    async for chunk in response.content.iter_any():
                        yield chunk.decode("utf-8")


    @classmethod
    def get_stored_sources(cls, job_id: str) -> tuple[list, list]:
        """
        Lấy web_sources đã lưu cho job_id.
        """
        web_sources = getattr(cls, '_stored_sources', {}).get(job_id, [])
        return web_sources, []


    @classmethod
    def store_sources(cls, job_id: str, web_sources: list):
        """
        Lưu web_sources cho job_id.
        """
        if not hasattr(cls, '_stored_sources'):
            cls._stored_sources = {}
        cls._stored_sources[job_id] = web_sources


    @classmethod
    async def _check_connection(cls, server: ServerStatus) -> bool:
        """
        Kiểm tra kết nối tới server bằng cách gọi /info.
        """
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
        """
        Cập nhật thông tin server. Nếu chưa có thì thêm mới.
        """
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