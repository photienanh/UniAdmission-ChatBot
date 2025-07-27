from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=1)
    
class AuthSuccess(BaseModel):
    success: Literal[True] = Field(True)
    redirect: str = Field(...)
    
class AuthFailed(BaseModel):
    success: Literal[False] = Field(False)
    message: str = Field(...)
