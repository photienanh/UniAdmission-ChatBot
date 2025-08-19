from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope

from config import IS_DEVELOPEMENT

from .utils import NO_CACHE_HEADERS

class CacheControledStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        if IS_DEVELOPEMENT:
            response.headers.update(NO_CACHE_HEADERS)
        return response
    
