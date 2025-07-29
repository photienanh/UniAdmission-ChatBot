import jwt
from datetime import datetime, timedelta, timezone
from config import SECRET_KEY

ALGORITHM = "HS256"

def generate_jwt(username: str, exp_hours: float = 1) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=exp_hours)   
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_jwt(token: str) -> str | jwt.ExpiredSignatureError | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.ExpiredSignatureError as e:
        return e
    except jwt.PyJWTError:
        return None
