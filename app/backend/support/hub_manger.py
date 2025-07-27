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
    async def register_provider(self, ws: WebSocket, client_type: str, name: str, uid: str):
        info = WebsocketInfo(
            ws=ws,
            client_type=client_type,
            name=name,
            uid=uid,
            result={}
        )
        old_instance = self.provider_wss.get(client_type, None)
        if old_instance != None:
            await old_instance.ws.close(code=1000, reason="Replaced by another instance")
            print(f"Removed old instance of {client_type}, name: {name}, uid: {uid}")
        self.provider_wss[client_type] = info
        print(f"Accept websocket from {name}, type: {client_type}, uid: {uid}")
    async def on_provider_ws_closed(self, client_type: str, uid: str):
        ws = self.provider_wss.pop(client_type, None)
        if not ws:
            print(f"Failed to close provider ws (provider not found): {client_type} | {uid}")
    async def consume(self, client_type: str, request_id: str, text: str):
        ws = self.provider_wss.get(client_type)
        if ws:
            uid = ws.uid
            await ws.ws.send_json({
                "request_id": request_id,
                "text": text
            })
            while True:
                ws = self.provider_wss.get(client_type)
                if ws and ws.uid == uid:
                    if request_id in ws.result:
                        return ws.result.pop(request_id)
                    await asyncio.sleep(self.poll)
                else:
                    return Exception("Provider aldready closed")
        else:
            print(f"Provider ws not registed")
    async def provide(self, client_type: str, request_id: str, text: str):
        ws = self.provider_wss.get(client_type)
        if ws:
            # print(request_id, text)
            ws.result[request_id] = text
        else:
            print(f"Provider ws not registed")