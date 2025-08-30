from typing import cast
from jwt import ExpiredSignatureError
from fastapi import Request, HTTPException
from sqlalchemy import select
import traceback

from database.manager import session               # session() context manager cho DB
from database.utils import decode_jwt, generate_jwt # hàm tạo / đọc JWT
from database.schema import User                   # ORM model User
from core.types import UserRole                    # Kiểu role (user / admin)
from config import JWT_DURATION                    # Thời gian sống của JWT

async def check_login(request: Request, role: UserRole = "user") -> User:
    """Kiểm tra JWT trong cookie -> trả về User nếu hợp lệ, 
       ngược lại raise HTTPException 401"""

    # Lấy token JWT từ cookie
    jwt = request.cookies.get("jwt")
    if not jwt:
        raise HTTPException(status_code=401, detail="No token found")

    # Giải mã JWT
    data = decode_jwt(jwt)
    if data == None: # token không hợp lệ
        raise HTTPException(status_code=401, detail="Invalid token")
    elif isinstance(data, ExpiredSignatureError): # token hết hạn
        raise HTTPException(status_code=401, detail="Expired token")

    # Nếu token OK -> unpack ra username, role
    username, role = data

    # Kiểm tra user trong DB
    async with session() as ss:
        user = (await ss.execute(select(User).filter_by(username=username))).scalar()
        if user:
            # Nếu chỉ yêu cầu role = "user" -> ai cũng pass
            if role == "user":
                return user
            # Nếu yêu cầu admin -> check role trong DB
            elif role == user.role:
                return user
            else:
                raise HTTPException(status_code=401, detail="User is not admin")
        else:
            raise HTTPException(status_code=401, detail="User not found")

async def login_user(username: str, password: str) -> str | None:
    """Trả về JWT nếu login thành công, ngược lại trả None"""

    async with session() as ss:
        # Tìm user trong DB theo username
        user = (await ss.execute(select(User).filter_by(username=username))).scalar()
        # Nếu tồn tại và password đúng
        if user and user.check_password(password):
            # Sinh JWT chứa username + role, với hạn JWT_DURATION
            jwt = generate_jwt(cast(str, user.username), user.role, JWT_DURATION)
            return jwt
        return None

async def logout_user(username: str) -> bool:
    """Trả về True nếu user tồn tại, False nếu không.
       (⚠️ Lưu ý: không thật sự revoke JWT, chỉ check user có tồn tại thôi)"""

    async with session() as ss:
        user = (await ss.execute(select(User).filter_by(username=username))).scalar()
        if user:
            return True
        return False

async def register_user(full_name: str, username: str, email: str, password: str, **kwargs) -> bool:
    """
    Đăng ký user mới.
    Commit ngay vào DB.
    Trả về True nếu thành công, False nếu username/email đã tồn tại hoặc có lỗi.
    """
    async with session() as ss:
        # Check username hoặc email đã tồn tại chưa
        user = (await ss.execute(
            select(User).filter((User.username == username) | (User.email == email))
        )).scalar()

        if not user: # Nếu chưa tồn tại
            user = User()
            user.full_name = full_name
            user.username = username
            user.email = email
            user.set_password(password) # hash password
            ss.add(user)

            try:
                await ss.commit() # lưu vào DB
                return True
            except Exception:
                await ss.rollback() # rollback nếu lỗi
                traceback.print_exc()
                return False
        return False

async def delete_user(user: User) -> bool:
    """
    Xóa user khỏi DB.
    Theo docstring: sẽ xóa luôn ChatSession và ChatMessage liên quan (cascade).
    Commit ngay.
    Trả về True nếu thành công, False nếu lỗi.
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
