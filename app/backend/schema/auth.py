import sys
if sys.version_info.minor >= 12:
    from typing import TypedDict
else:
    from typing_extensions import TypedDict
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from urllib.parse import parse_qsl

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    @classmethod
    def parse(cls, b: bytes):
        form_data = dict(parse_qsl(b.decode()))
        return LoginRequest(**form_data)
class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=1)
    @classmethod
    def parse(cls, b: bytes):
        form_data = dict(parse_qsl(b.decode()))
        return RegisterRequest(**form_data)
    
class DeleteAccountRequest(TypedDict):
    confirm: str
    password: str
    
class AuthSuccess(TypedDict):
    success: Literal[True]
    redirect: str
    
class AuthFailed(TypedDict):
    success: Literal[False]
    message: str
    
