from typing import Any
from typing_extensions import Annotated, Doc
from fastapi.responses import JSONResponse
from starlette.background import BackgroundTask
from fastapi import HTTPException

class SuccessResponse(JSONResponse):
    def __init__(self, message: str) -> None:
        super().__init__({"message": message, "success": True}, 200)
class FailedResponse(JSONResponse):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__({"message": message, "success": False}, status_code=status_code)

class ServerError(HTTPException):
    def __init__(self, detail: Any) -> None:
        super().__init__(500, detail)
        
NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0"
}