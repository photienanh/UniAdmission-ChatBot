from fastapi import APIRouter, Request, Body
from fastapi.responses import Response, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Union

from .database import (
    login_user, register_user, check_login, logout_user, delete_all_user_data,
    DBSession
)
from .schema import (
    SuccessResponse, FailedResponse, ErrorReponse, ServerError, NO_CACHE_HEADERS,
    LoginRequest, RegisterRequest, DeleteAccountRequest, AuthFailed, AuthSuccess
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def set_jwt(response: Response, jwt: str):
    response.set_cookie(
        key="jwt",
        value=jwt,
        httponly=True,
        secure=False, # http
        samesite="lax",
        max_age=3600
    )
    return response

@router.get("/login", name="login", response_class=HTMLResponse)
def get_login(request: Request):
    def get_flashed_messages():
        return request.session.pop("_messages", [])
    return templates.TemplateResponse(
        "login.html", 
        {"request": request, "get_flashed_messages": get_flashed_messages}
    )

@router.get("/register", name="register", response_class=HTMLResponse)
def get_register(request: Request):
    def get_flashed_messages():
        return request.session.pop("_messages", [])
    return templates.TemplateResponse(
        "register.html", 
        {"request": request, "get_flashed_messages": get_flashed_messages}
    )

@router.get("/delete_account", name="delete_account", response_class=HTMLResponse)
def get_delete(request: Request):
    user = check_login(request)
    return templates.TemplateResponse("delete_account.html", {"request": request, "current_user": user})

@router.post("/login", responses={200: {"model": AuthSuccess}, 400: {"model": AuthFailed}})
def post_login(
    request: Union[LoginRequest, dict, bytes] = Body(LoginRequest), # Union to prevent auto 422 error
):
    if isinstance(request, bytes): # When request is Form
        try:
            request = LoginRequest.parse(request)
        except: pass
    if not isinstance(request, LoginRequest): return FailedResponse("Dữ liệu không hợp lệ")
    jwt = login_user(request.username, request.password)
    if jwt:
        response = JSONResponse({
            "success": True,
            "redirect": "/"
        })
        set_jwt(response, jwt)
        return response
    else:
        return FailedResponse("Tên đăng nhập hoặc mật khẩu không đúng")
    
@router.post("/register", responses={200: {"model": AuthSuccess}, 400: {"model": AuthFailed}})
async def post_register(
    request: Union[RegisterRequest, dict, bytes] = Body(RegisterRequest), # Union to prevent auto 422 error
):
    if isinstance(request, bytes): # When request is Form
        try:
            request = RegisterRequest.parse(request)
        except: pass
    if not isinstance(request, RegisterRequest): # Validation failed
        return FailedResponse("Dữ liệu không hợp lệ")
    if register_user(request.full_name, request.username, request.email, request.password):
        jwt = login_user(request.username, request.password)
        if not jwt: raise ServerError("Failed to auto login")
        response = RedirectResponse(url="/")
        set_jwt(response, jwt)
        return response
    else:
        return FailedResponse("Tên người dùng hoặc email đã tồn tại")

@router.get("/logout")
def get_logout(request: Request):
    user = check_login(request)
    if logout_user(user.username):
        response = RedirectResponse(url="/login")
        response.delete_cookie('jwt') # Delete jwt, it still usable through
        response.headers.update(NO_CACHE_HEADERS)
        return response
    else:
        raise ServerError("Failed to logout")
    
@router.post("/delete_account")
def post_delete(request: Request, data: DeleteAccountRequest):
    """Xóa tài khoản người dùng"""
    user = check_login(request)
    if data.confirm != "DELETE":
        return FailedResponse('Vui lòng nhập "DELETE" để xác nhận')
    if not user.check_password(data.password):
        return FailedResponse("Mật khẩu không đúng")
    try:
        delete_all_user_data(user)
        login_user(user.username, data.password)
        DBSession.commit()
        return SuccessResponse("Tài khoản đã được xóa thành công")
    except Exception as e:
        DBSession.rollback()
        return FailedResponse("Đã có lỗi xảy ra")
    