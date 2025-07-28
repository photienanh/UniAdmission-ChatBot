from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal, Any
from datetime import datetime

class ModelInfo(BaseModel):
    name: str = Field(...)
    model_type: str = Field(...)