import jwt
from datetime import datetime, timedelta, timezone

from config import JWT_ALGORITHM, JWT_SECRET_KEY    # Config: thuật toán JWT (HS256) và secret key
from core.types import UserRole                     # Kiểu dữ liệu cho role (user / admin)

# Hàm tạo JWT
def generate_jwt(username: str, role: str, exp_seconds: float = 1) -> str:
    # Payload của JWT
    payload = {
        "sub": username,   # subject: username (dùng để nhận diện user)
        "role": role,      # role: quyền hạn (user / admin)
        "exp": datetime.now(timezone.utc) + timedelta(seconds=exp_seconds)   
        # exp: thời gian hết hạn (UTC)
    }
    # Encode payload thành JWT string, ký bằng secret key và thuật toán
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


# Hàm giải mã và kiểm tra JWT
def decode_jwt(token: str) -> tuple[str, UserRole] | jwt.ExpiredSignatureError | None:
    """
    Trả về (username, role) nếu decode thành công
    Trả về jwt.ExpiredSignatureError nếu token hết hạn
    Trả về None nếu token sai hoặc lỗi khác
    """
    try:
        # Decode token, verify bằng secret key và thuật toán
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload.get("sub"), payload.get("role")
    except jwt.ExpiredSignatureError as e:
        # Nếu token hết hạn -> trả về exception này
        return e
    except jwt.PyJWTError:
        # Các lỗi khác (sai chữ ký, token giả mạo, token hỏng) -> trả None
        return None