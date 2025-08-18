from fastapi import Request, Response
from datetime import datetime, timezone
from fastapi.responses import JSONResponse

from config import JWT_DURATION

def set_jwt(response: Response, jwt: str):
    response.set_cookie(
        key="jwt",
        value=jwt,
        httponly=True,
        secure=False, # http
        samesite="lax",
        max_age=JWT_DURATION
    )
    
NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0"
}

def get_timestamp() -> datetime:
    return datetime.now(timezone.utc)

class CommonResponse(JSONResponse):
    def __init__(self, status_code: int, success: bool, detail: str, next: str | None = None) -> None:
        content = {
            "success": success,
            "detail": detail,
        }
        if next != None:
            content["next"] = next
        super().__init__(status_code=status_code, content=content)