from core.types import UserRole
from .base import *

# Does not prevent user from login in multiple devices at sammetime, with different session token
class User(Base): #type:ignore
    __tablename__ = "user"
    
    id = cast(str, Column(String(36), primary_key=True, default=generate_id))
    role = cast(UserRole, Column(String(10), default="user"))
    username = cast(str, Column(String(100), unique=True, nullable=False))
    email = cast(str, Column(String(254), unique=True, nullable=False))
    password_hash = cast(str, Column(String(120), nullable=False))
    full_name = cast(str, Column(Text, nullable=False))
    
    sessions = relationship("ChatSession", backref="user", lazy=True, cascade="all, delete-orphan")
    
    def set_password(self, password: str):
        """No auto commit"""
        self.password_hash = generate_password_hash(password)
    def check_password(self, password: str):
        return check_password_hash(self.password_hash, password)
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name
        }