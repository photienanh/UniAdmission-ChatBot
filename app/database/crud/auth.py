from typing import cast
from jwt import ExpiredSignatureError
from fastapi import Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import traceback

from database.manager import session
from database.utils import decode_jwt, generate_jwt
from database.schema import User
from core.types import UserRole
from config import JWT_DURATION

async def check_login(request: Request, role: UserRole = "user") -> User:
    """Raise `HTTPException` if jwt not found or invalid"""
    jwt = request.cookies.get("jwt")
    if not jwt:
        raise HTTPException(status_code=401, detail="No token found")
    data = decode_jwt(jwt)
    if data == None:
        raise HTTPException(status_code=401, detail="Invalid token")
    elif isinstance(data, ExpiredSignatureError):
        raise HTTPException(status_code=401, detail="Expired token")
    username, role = data
    async with session() as ss:
        user = (await ss.execute(select(User).filter_by(username=username))).scalar()
        if user:
            if role == "user": # Skip permission check if required role is user
                return user
            elif role == user.role: # Check permission when required role is admin
                    return user
            else:
                raise HTTPException(status_code=401, detail="User is not admin")
        else:
            raise HTTPException(status_code=401, detail="User not found")
        
async def login_user(username: str, password: str) -> str | None:
    """Return jwt on success else `None`"""
    async with session() as ss:
        user = (await ss.execute(select(User).filter_by(username=username))).scalar()
        if user and user.check_password(password):
            jwt = generate_jwt(cast(str, user.username), user.role, JWT_DURATION)
            return jwt
        return None

async def logout_user(username: str) -> bool:
    """Return `True` on success else `False`"""
    async with session() as ss:
        user = (await ss.execute(select(User).filter_by(username=username))).scalar()
        if user:
            return True
        return False

async def register_user(full_name: str, username: str, email: str, password: str, **kwargs) -> bool:
    """
    Auto commit.\n
    Return `True` on success else `False`
    """
    async with session() as ss:
        user = (await ss.execute(select(User).filter((User.username == username) | (User.email == email)))).scalar() #type:ignore
        if not user:
            user = User()
            user.full_name = full_name
            user.username = username
            user.email = email
            user.set_password(password)
            ss.add(user)
            try:
                await ss.commit()
                return True
            except Exception:
                await ss.rollback()
                traceback.print_exc()
                return False
        return False

async def delete_user(user: User) -> bool:
    """
    Auto commit.\n
    Delete all `User` data, along with their `ChatSession` and `ChatMessage`.\n
    Return `True` on success else `False`
    """
    async with session() as ss:
        try:
            await ss.delete(user)
            await ss.commit()
            return True
        except Exception:
            await ss.rollback()
            traceback.print_exc()
            return False