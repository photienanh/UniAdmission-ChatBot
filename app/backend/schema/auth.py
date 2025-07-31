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
class DeleteAccountRequest(BaseModel):
    confirm: str
    password: str
    
class AuthSuccess(BaseModel):
    success: Literal[True] = Field(True)
    redirect: str
    
class AuthFailed(BaseModel):
    success: Literal[False] = Field(False)
    message: str
    
