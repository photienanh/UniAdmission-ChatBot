from aiohttp.client import ClientSession
import asyncio
from typing import TypedDict, Optional
class APIJobInfo(TypedDict):
    model_id: str
    message: str
    lora_request: Optional[dict]
    sampling_params: dict
class APIJobResult(TypedDict):
    text: list[str]
    