from fastapi import FastAPI
from typing import Awaitable, AsyncGenerator, Callable
from contextlib import asynccontextmanager
from fastapi import FastAPI
import aiohttp
import asyncio
import traceback

from .schema import WorkerServerInfo, ModelPreOutput, WorkerChatRequest, WorkerStoreChatData
from .router import router

async def kaggle_register(server_domain: str, info: WorkerServerInfo):
    async with aiohttp.ClientSession() as ss:
        url = f"{server_domain}/worker/register"
        async with ss.post(url, json=info) as response:
            if response.ok:
                pass
            else:
                print(f"[Worker] Failed to update server info")
async def get_nrok_url() -> str:
    async with aiohttp.ClientSession() as ss:
        url = f"http://127.0.0.1:4040/api/tunnels"
        async with ss.get(url) as response:
            if response.ok:
                tunnels = (await response.json())["tunnels"]
                for tunnel in tunnels:
                    return tunnel["public_url"]
    raise Exception("No tunnel")
async def connection_task(server_domain: str, info: WorkerServerInfo, poll: float):
    try:
        while True:
            try:
                await kaggle_register(server_domain, info)
                # print(f"[Kaggle] Ping ...")
            except:
                pass
            await asyncio.sleep(poll)
    except asyncio.CancelledError: # Fired when shutdown server
        pass
async def store_chat(server_domain: str, data: WorkerStoreChatData):
    try:
        async with aiohttp.ClientSession() as ss:
            url = f"{server_domain}/worker/store_chat"
            async with ss.post(url, json=data) as response:
                if response.ok:
                    return True
                else:
                    return False
    except:
        traceback.print_exc()
def construct_app(
        server_domain: str,
        info: WorkerServerInfo,
        pre_inference: Callable[[WorkerChatRequest], Awaitable[ModelPreOutput]],
        inferece: Callable[[str], AsyncGenerator[str, None]],
        init_tasks: list[Awaitable] = [],
        shutdown_tasks: list[Awaitable] = [],
        update_poll: float = 10,
        is_local: bool = False
    ):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        if not is_local:
            info["domain"] = await get_nrok_url()
            print(f"Domain: {info['domain']}")

        for task in init_tasks:
            await task
            
        asyncio.create_task(connection_task(server_domain, info, update_poll))
        yield # Return control to FastAPI app
        
        # Shutdown
        for task in shutdown_tasks:
            await task
    app = FastAPI(lifespan=lifespan)
    app.include_router(router, tags=["Server"])
    app.state.info = info
    app.state.pre_inference = pre_inference
    app.state.inference = inferece
    async def store_chat_function(data: WorkerStoreChatData):
        return await store_chat(server_domain, data)
    app.state.store_chat = store_chat_function
    return app