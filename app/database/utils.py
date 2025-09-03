import jwt
from datetime import datetime, timedelta, timezone

from config import JWT_ALGORITHM, JWT_SECRET_KEY
from core.types import UserRole

def generate_jwt(username: str, role: str, exp_seconds: float = 1) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=exp_seconds)   
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_jwt(token: str) -> tuple[str, UserRole] | jwt.ExpiredSignatureError | None:
    """
    Return (username, role) on success, jwt.ExpiredSignatureError when token is expired and None when error occur
    Args:
        token (str): jwt token
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload.get("sub"), payload.get("role")
    except jwt.ExpiredSignatureError as e:
        return e
    except jwt.PyJWTError:
        return None