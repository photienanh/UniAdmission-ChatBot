from fastapi import FastAPI
from typing import Awaitable, AsyncGenerator, Callable
from contextlib import asynccontextmanager
from fastapi import FastAPI
import aiohttp

from .schema import KaggleServerInfo, ModelPreOutput, KaggleRequest
from .router import router

async def kaggle_register(server_domain: str, info: KaggleServerInfo):
    async with aiohttp.ClientSession() as ss:
        url = f"{server_domain}/kaggle"
        async with ss.post(url, json=info) as response:
            if response.ok:
                pass
            else:
                raise Exception(f"Failed to register") #TODO: Retry
async def get_nrok_url() -> str:
    async with aiohttp.ClientSession() as ss:
        url = f"http://127.0.0.1:4040/api/tunnels"
        async with ss.get(url) as response:
            if response.ok:
                tunnels = (await response.json())["tunnels"]
                for tunnel in tunnels:
                    return tunnel["public_url"]
    raise Exception("No tunnel")
def construct_app(
        server_domain: str,
        info: KaggleServerInfo,
        pre_inference: Callable[[KaggleRequest], Awaitable[ModelPreOutput]],
        inferece: Callable[[str], Awaitable[AsyncGenerator[str, None]]],
        init_tasks: list[Awaitable] = []
    ):
    @asynccontextmanager
    async def local_lifespan(app: FastAPI):
        # Startup
        info["domain"] = await get_nrok_url()
        print(f"Domain: {info['domain']}")

        for task in init_tasks:
            await task
        await kaggle_register(server_domain, info)
        yield # Return control to FastAPI app
        
        # Shutdown
    app = FastAPI(lifespan=local_lifespan)
    app.include_router(router, tags=["Server"])
    app.state.info = info
    app.state.pre_inference = pre_inference
    app.state.inference = inferece
    return app