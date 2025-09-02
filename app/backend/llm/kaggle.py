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
                # Server approved và không bị block thì dùng luôn
                server_id = server["info"].get("server_id")
                if server_id:
                    from backend.route.admin import AdminManager
                    if not AdminManager.is_server_approved(server_id):
                        # Server chưa approve → không dùng
                        continue
                    if AdminManager.is_server_blocked(server_id):
                        # Server bị block → không dùng
                        continue
                
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
        if vector_sources:
            request["vector_sources"] = vector_sources
        
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

                    except Exception as e:
                        # Nếu lỗi kết nối thì retry
                        pass

                    # Đợi cho server timeout rồi thử server khác
                    await asyncio.sleep(KAGGLE_RETRY_DELAY)
                    await cls.get_models()  # Cleanup server chết
                    server = await cls.get_available_server(model_id)
                    retry += 1
                else:
                    break

        return None


    @classmethod
    async def inference(cls, domain: str, job_id: str) -> AsyncGenerator[str, None]:
        """
        Gửi request inference tới server Kaggle và stream output về.
        """
        # Kiểm tra domain có bị block không
        server_id = domain.replace("https://", "").replace("http://", "")
        from backend.route.admin import AdminManager
        if AdminManager.is_server_blocked(server_id):
            # Server bị block → không thực hiện inference
            yield "[ERROR] Server is blocked and cannot be accessed."
            return
            
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
    async def get_available_servers(cls, model_id: str) -> list:
        """Check which servers are available (not blocked) for the given model_id"""
        from ..route.admin import AdminManager
        
        # Use KaggleManager._servers which contains the actual server info with models
        all_servers = cls._servers
        
        # Filter servers for the model_id (check models in the server info)
        model_servers = []
        for server in all_servers:
            server_info = server.get("info", {})
            models = server_info.get("models", [])
            
            # Check if this server has the requested model
            for model in models:
                if model.get("id") == model_id:
                    model_servers.append(server)
                    break
        
        # Filter out servers that are not approved or are blocked
        available_servers = []
        for server in model_servers:
            server_info = server.get("info", {})
            domain = server_info.get("domain", "")
            
            # Extract server_id from domain (remove https:// prefix)
            domain_as_server_id = domain.replace("https://", "").replace("http://", "")
            
            # Check if server is approved and not blocked
            if AdminManager.is_server_approved(domain_as_server_id) and not AdminManager.is_server_blocked(domain_as_server_id):
                available_servers.append(server)
        
        return available_servers


    @classmethod
    async def _check_connection(cls, server: ServerStatus) -> bool:
        """
        Kiểm tra kết nối tới server bằng cách gọi /info.
        """
        # Kiểm tra server có bị block không
        server_id = server["info"].get("server_id")
        if server_id:
            from backend.route.admin import AdminManager
            if AdminManager.is_server_blocked(server_id):
                # Server bị block → không check connection
                return False
                
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
        Chỉ cho phép server đã được approve và không bị block.
        """
        # Check server permissions - chỉ cần approve một lần và không bị block
        server_id = info.get("server_id")
        if server_id:
            from backend.route.admin import AdminManager
            if not AdminManager.is_server_approved(server_id):
                return
            if AdminManager.is_server_blocked(server_id):
                # Nếu server bị block, xóa nó khỏi danh sách nếu có
                cls._servers = [s for s in cls._servers if s["info"]["domain"] != info["domain"]]
                return
        
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