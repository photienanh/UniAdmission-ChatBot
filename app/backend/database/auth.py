from typing import cast
from .models import DBSession, User, ChatSession, ChatMessage
from .jwt_ import generate_jwt, decode_jwt
from jwt import ExpiredSignatureError
from .models import User
from fastapi import Request, HTTPException


def check_login(request: Request) -> User:
    """
    Raise HTTPException if jwt not found or invalid
    """
    request = cast(Request, request)
    jwt = request.cookies.get("jwt")
    if not jwt:
        raise HTTPException(status_code=401, detail="No token found")
    username = decode_jwt(jwt)
    if username == None:
        raise HTTPException(status_code=401, detail="Invalid token")
    elif isinstance(username, ExpiredSignatureError):
        raise HTTPException(status_code=401, detail="Expired token")  
    user = DBSession.session.query(User).filter_by(username=username).first()
    if user:
        return user
    else:
        raise HTTPException(status_code=401, detail="User not found")  
            
def login_user(username: str, password: str) -> str | None:
    """
    Return jwt on success else None
    """
    user = DBSession.session.query(User).filter_by(username=username).first()
    if user and user.check_password(password):
        user.is_active = True
        DBSession.commit()
        jwt = generate_jwt(cast(str, user.username), exp_hours=24)
        return jwt
    return None
    
def logout_user(username: str) -> bool:
    """
    Return true on success else false
    """
    user = DBSession.session.query(User).filter_by(username=username).first()
    if user and user.is_active:
        user.is_active = False
        DBSession.commit() # HMM, Do we need to destroy jwt ?
        return True
    return False
    
def register_user(full_name: str, username: str, email: str, password: str) -> bool:
    """
    Return true on success else false
    """
    user = DBSession.session.query(User).filter((User.username == username) | (User.email == email)).first() #type:ignore
    if not user:
        user = User()
        user.full_name = full_name
        user.username = username
        user.email = email
        user.set_password(password)
        DBSession.session.add(user)
        DBSession.commit()
        return True
    return False

def delete_all_user_data(user: User):
    DBSession.session.delete(user) #cascade delete
