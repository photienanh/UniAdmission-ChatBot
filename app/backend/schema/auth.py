from pydantic import BaseModel, Field, EmailStr

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=256)
    
class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=1024)
    username: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=256)
    
class DeleteAccountRequest(BaseModel):
    confirm: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=256)