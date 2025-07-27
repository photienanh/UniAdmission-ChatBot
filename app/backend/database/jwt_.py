import jwt
from datetime import datetime, timedelta, timezone

SECRECT_KEY = "dhjowiu4910nuviocq3jorxmhoimfjfjajkjif0mx"
ALGORITHM = "HS256"

def generate_jwt(username: str, exp_hours: float = 1) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=exp_hours)   
    }
    return jwt.encode(payload, SECRECT_KEY, algorithm=ALGORITHM)

def decode_jwt(token: str) -> str | jwt.ExpiredSignatureError | None:
    try:
        payload = jwt.decode(token, SECRECT_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.ExpiredSignatureError as e:
        return e
    except jwt.PyJWTError:
        return None
