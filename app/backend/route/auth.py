from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response, JSONResponse, RedirectResponse
from typing import Union

from database import check_login, login_user, register_user, logout_user, delete_user
from backend.schema import LoginRequest, RegisterRequest, DeleteAccountRequest

from .utils import set_jwt, NO_CACHE_HEADERS, CommonResponse

router = APIRouter()

@router.post("/check")
async def check_token(request: Request):
    _ = await check_login(request)
    return CommonResponse(200, True, "Valid")

@router.post("/login")
async def login(request: LoginRequest):
    jwt = await login_user(request.username, request.password)
    if jwt:
        response = CommonResponse(200, True, "Đăng nhập thành công", "/")
        set_jwt(response, jwt)
        return response
    else:
        return CommonResponse(401, False, "Tên đăng nhập hoặc mật khẩu không đúng")
    
@router.post("/register")
async def register(request: RegisterRequest):
    success = await register_user(request.full_name, request.username, request.email, request.password)
    if success:
        jwt = await login_user(request.username, request.password)
        if not jwt: 
            return CommonResponse(200, True, "Đăng ký thành công !", "/login")
        else:
            response = CommonResponse(200, True, "Đăng ký thành công", "/")
            set_jwt(response, jwt)
            return response
    else:
        return CommonResponse(401, False, "Tên người dùng hoặc email đã tồn tại")
            
@router.post("/logout")
async def logout(request: Request):
    user = await check_login(request)
    success = await logout_user(user.username)
    if success:
        response = CommonResponse(200, True, "Đăng xuất thành công", "/login")
        response.delete_cookie("jwt") # Delete jwt, it still usable though
        response.headers.update(NO_CACHE_HEADERS)
        return response
    else:
        return CommonResponse(500, False, "Đăng xuất thất bại")
    
    
@router.post("/delete_account")
async def delete_account(request: Request, data: DeleteAccountRequest):
    user = await check_login(request)
    if data.confirm != "DELETE":
        return CommonResponse(400, False, 'Vui lòng nhập "DELETE" để xác nhận')
    if not user.check_password(data.password):
        return CommonResponse(401, False, "Mật khẩu không đúng")
    success = await delete_user(user)
    if success:
        return CommonResponse(200, True, "Tài khoản đã được xóa thành công", "/login")
    else:
        return CommonResponse(500, False, "Đã có lỗi xảy ra")
        