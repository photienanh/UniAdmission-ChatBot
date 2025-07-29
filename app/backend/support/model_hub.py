from fastapi import WebSocket
from typing import NamedTuple
import asyncio

class WebsocketInfo(NamedTuple):
    ws: WebSocket
    client_type: str
    name: str
    uid: str
    result: dict[str, str]
    
class ProviderHub:
    def __init__(self) -> None:
        self.provider_wss: dict[str, WebsocketInfo] = {}
        self.poll = 0.1