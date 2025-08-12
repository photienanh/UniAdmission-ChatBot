from typing import Any
import uvicorn
from vllm.engine.async_llm_engine import AsyncEngineDeadError
from vllm.engine.multiprocessing import MQEngineDeadError
from vllm.v1.engine.exceptions import EngineDeadError, EngineGenerateError
from http import HTTPStatus
import signal
import vllm.envs as envs
from vllm.utils import find_process_using_port
import os
from fastapi import FastAPI, Response, Request
import asyncio

from vllm.logger import init_logger

logger = init_logger("vllm.entrypoints.api_server")
async def serve_http(
    app: FastAPI,
    **uvicorn_kwargs: Any
) -> tuple[uvicorn.Server, Any]: 
    from vllm import __version__
    logger.info(f"[vLLM] vLLM API server version {__version__}")
    logger.info(f"[vLLM] Server started at {os.getpid()}")
    logger.info("Available route are:")
    for route in app.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if methods is None or path is None:
            continue
        logger.info(f"Route: {path}, Methods: {', '.join(methods)}")

    config = uvicorn.Config(app, **uvicorn_kwargs)
    config.load()
    server = uvicorn.Server(config)
    loop = asyncio.get_running_loop()
    server_task = loop.create_task(server.serve(sockets=None))
    def signal_handler() -> None:
        server_task.cancel()
    loop.add_signal_handler(signal.SIGINT, signal_handler)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)
    try:
        await server_task
    except asyncio.CancelledError:
        port = uvicorn_kwargs.get("port", 8000)
        process = find_process_using_port(port)
        if process is not None:
            logger.debug(f"Port {port} is being used by process {process}")
        logger.info("Shutting down FastAPI HTTP Server")
    return server, logger