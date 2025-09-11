from typing import Protocol, AsyncGenerator
import enum
from fastapi import FastAPI
import weakref

from .schema import GenerationParams, WorkerChatRequest, ModelPreOutput, WorkerStoreChatData

class CallType(enum.Enum):
    ROUTER = "router"
    KEYWORDS = "keywords"
    RANKER = "page_ranker"
    READER = "reader"
    
class ModelProtocol(Protocol):
    async def __call__(self, call_type: CallType | str, instruction: str, prompt: str, params: GenerationParams) -> AsyncGenerator[str, None]: ...
    
class ServerModel:
    def set_app(self, app: FastAPI) -> None:
        self._app_ref = weakref.ref(app) # Prevent loop reference
    async def pre_inference(self, request: WorkerChatRequest) -> ModelPreOutput:
        raise NotImplementedError()
    def inference(self, stream_id: str) -> AsyncGenerator[str, None]:
        raise NotImplementedError()
    async def store(self, data: WorkerStoreChatData):
        app: FastAPI | None = self._app_ref()
        if app:
            await app.state.store_chat(data)
        else:
            raise Exception("ServerModel App is None")