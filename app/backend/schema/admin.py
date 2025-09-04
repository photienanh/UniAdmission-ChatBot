from pydantic import BaseModel
from typing import List, Optional, Literal

class AdminKaggleRequest(BaseModel):
    """Schema for Kaggle worker access request"""
    server_id: str
    request_type: Literal["server_registration", "package_download", "model_registration"]
    requested_packages: List[str] = []
    reason: str = ""
    contact_info: str = ""
    ngrok_url: Optional[str] = None

class AdminKaggleApproval(BaseModel):
    """Schema for admin approval/rejection"""
    admin_notes: str = ""

