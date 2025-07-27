from fastapi import APIRouter, Request, Body, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Union, Any, cast

from .database import login_user, register_user, check_login, logout_user, delete_all_user_data, DBSession
from .schema import LoginRequest, RegisterRequest, DeleteAccountRequest, AuthFailed, AuthSuccess

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def flash(request: Request, message: str):
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append(message)
    

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
    if isinstance(request, bytes): # Validation failed
        try:
            request = LoginRequest.parse(request)
        except:
            pass
    if not isinstance(request, LoginRequest):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Dữ liệu không hợp lệ"
            }
        )
    jwt = login_user(request.username, request.password)
    if jwt:
        response = JSONResponse(
            status_code=307,
            content={
            "success": True,
            "redirect": "/"
        })
        response.set_cookie(
            key="jwt",
            value=jwt,
            httponly=True,
            secure=False, # http
            samesite="lax",
            max_age=3600
        )
        return response
    else:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Tên đăng nhập hoặc mật khẩu không đúng"
            }
        )

@router.post("/register", responses={200: {"model": AuthSuccess}, 400: {"model": AuthFailed}})
async def post_register(
    request: Union[RegisterRequest, dict, bytes] = Body(RegisterRequest), # Union to prevent auto 422 error
):
    if isinstance(request, bytes):
        try:
            request = RegisterRequest.parse(request)
        except:
            pass
    if not isinstance(request, RegisterRequest): # Validation failed
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Dữ liệu không hợp lệ"
            }
        )   
    if register_user(request.full_name, request.username, request.email, request.password):
        return RedirectResponse(url="/login")
    else:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Tên người dùng hoặc email đã tồn tại"
            }
        )


@router.get("/logout")
def get_logout(request: Request):
    user = check_login(request)
    if logout_user(user.username):
        response = RedirectResponse(url="/login")
        response.delete_cookie('jwt') # Delete jwt, it still usable through
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    else:
        raise HTTPException(status_code=500, detail="Failed to logout")
    
@router.post("/delete_account")
def post_delete(request: Request, data: DeleteAccountRequest):
    """Xóa tài khoản người dùng"""
    user = check_login(request)
    if data.confirm != "DELETE":
        return JSONResponse(content={
            "success": False,
            "message": 'Vui lòng nhập "DELETE" để xác nhận'
        })
    if not user.check_password(data.password):
        return JSONResponse(content={
            "success": False,
            "message": "Mật khẩu không đúng"
        })    
    try:
        delete_all_user_data(user)
        login_user(user.username, data.password)
        DBSession.commit()
        return JSONResponse(content={
            "success": True,
            "message": "Tài khoản đã được xóa thành công"
        })
    except Exception as e:
        DBSession.rollback()
        return JSONResponse(content={
            "success": False,
            "message": "Đã có lỗi xảy ra"
        })
    