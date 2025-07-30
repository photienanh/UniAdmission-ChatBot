from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable, Awaitable
from starlette.middleware.sessions import SessionMiddleware
from .schema import NO_CACHE_HEADERS

class NoCacheOnDeleteMiddleWare(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response: Response = await call_next(request)
        if request.url.path in ['/delete_account']:
            response.headers.update(NO_CACHE_HEADERS)
        return response
    
