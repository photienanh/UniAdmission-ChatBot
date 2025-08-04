import uuid
from ..schema import *
import time
import asyncio
import uuid
from typing import Optional

class ConnectionInfo(ClientInfo):
    timestamp: float    
    input_queue: list[tuple[str, ModelInput]]
    output_queue: list[tuple[str, ModelOutput | str]]

class ModelHub:
    def __init__(self) -> None:
        self.timeout = 5
        self.poll = 0.1
        self.maintain_poll = 0.5
        self.connections: dict[str, ConnectionInfo] = {}
        self.started = False
        self.running = True
    def _start(self):
        if self.started: return
        self.started = True
        async def task():
            while self.running:
                self._maintain()
                await asyncio.sleep(self.maintain_poll)
        asyncio.create_task(task())
    def _maintain(self):
        marked_for_delete: list[str] = []
        now = time.time()
        for connection in self.connections.values():
            if now - connection["timestamp"] > self.timeout:
                marked_for_delete.append(connection["uid"])
        for key in marked_for_delete:
            self.connections.pop(key)
            print(f"Connection disconnected: {key}")
    def _keep_alive(self, info: ClientInfo):
        self._start()
        connection = self.connections.get(info["uid"], None)
        if connection == None:
            connection = ConnectionInfo(
                name=info["name"],
                uid=info["uid"],
                models=info["models"],
                timestamp=0,
                input_queue=[],
                output_queue=[]
            )
            self.connections[info["uid"]] = connection
            print(f"New connection: {info['name']}")
        connection["timestamp"] = time.time()
    def get_alive_list(self) -> list[ModelInfo]:
        result = []
        for connection in self.connections.values():
            result.extend(connection["models"])
        return result
    def get_request(self, info: ClientInfo) -> Optional[RequestData]:
        self._keep_alive(info)
        connection = self.connections[info["uid"]]
        if len(connection["input_queue"]) > 0:
            job_id, model_input = connection["input_queue"].pop(0)
            return RequestData(
                job_id=job_id,
                payload=model_input
            )
    def set_response(self, info: ClientInfo, response: ResponseData):
        self._keep_alive(info)
        connection = self.connections[info["uid"]]
        connection["output_queue"].append((response["job_id"], response["payload"]))
    def set_error(self, info: ClientInfo, response: ErrorData):
        self._keep_alive(info)
        connection = self.connections[info["uid"]]
        connection["output_queue"].append((response["job_id"], response["error"]))

    async def inference(self, input: ModelInput) -> ModelOutput | str:
        model_id = input["model_id"]
        job_id = str(uuid.uuid4())
        for connection in self.connections.values():
            if model_id in [model_info["id"] for model_info in connection["models"]]:
                connection["input_queue"].append((job_id, input))
                while model_id in [model_info["id"] for model_info in connection["models"]]:
                    for index, (o_job_id, output) in enumerate(connection["output_queue"]):
                        if o_job_id == job_id:
                            connection["output_queue"].pop(index)
                            return output
                    await asyncio.sleep(self.poll)
                return "Client disconnected"
        raise KeyError(model_id)
    