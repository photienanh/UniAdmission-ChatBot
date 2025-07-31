from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal, Any
from datetime import datetime

class ModelInfo(BaseModel):
    name: str
    model_type: str