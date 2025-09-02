from fastapi import FastAPI
from typing import Awaitable, AsyncGenerator, Callable
from contextlib import asynccontextmanager
from fastapi import FastAPI
import aiohttp
import asyncio

from .schema import KaggleServerInfo, ModelPreOutput, KaggleRequest
from .router import router

async def kaggle_register(server_domain: str, info: KaggleServerInfo):
    async with aiohttp.ClientSession() as ss:
        url = f"{server_domain}/kaggle"
        async with ss.post(url, json=info) as response:
            if response.ok:
                pass
            else:
                print(f"[Kaggle] Failed to update server info")
            # else:
            #     raise Exception(f"Failed to register") #TODO: Retry

async def get_nrok_url() -> str:
    async with aiohttp.ClientSession() as ss:
        url = f"http://127.0.0.1:4040/api/tunnels"
        async with ss.get(url) as response:
            if response.ok:
                tunnels = (await response.json())["tunnels"]
                for tunnel in tunnels:
                    return tunnel["public_url"]
    raise Exception("No tunnel")

async def connection_task(server_domain: str, info: KaggleServerInfo, poll: float):
    try:
        while True:
            await kaggle_register(server_domain, info)
            # print(f"[Kaggle] Ping ...")
            await asyncio.sleep(poll)
    except asyncio.CancelledError:
        pass
    
def construct_app(
        server_domain: str,
        info: KaggleServerInfo,
        pre_inference: Callable[[KaggleRequest], Awaitable[ModelPreOutput]],
        inferece: Callable[[str], Awaitable[AsyncGenerator[str, None]]],
        init_tasks: list[Awaitable] = [],
        update_poll: float = 10
    ):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        info["domain"] = await get_nrok_url()
        print(f"Domain: {info['domain']}")

        for task in init_tasks:
            await task
            
        await kaggle_register(server_domain, info)
        asyncio.create_task(connection_task(server_domain, info, update_poll))
        yield # Return control to FastAPI app
        
        # Shutdown
    app = FastAPI(lifespan=lifespan)
    app.include_router(router, tags=["Server"])
    app.state.info = info
    app.state.server_domain = server_domain
    app.state.pre_inference = pre_inference
    app.state.inference = inferece
    return app