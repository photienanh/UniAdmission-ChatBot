from fastapi import APIRouter, Request, Body, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Union

from .database import login_user, register_user
from .schema import LoginRequest, RegisterRequest, AuthFailed, AuthSuccess

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/login", name="login", response_class=HTMLResponse)
async def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register", name="register", response_class=HTMLResponse)
async def get_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/login", responses={200: {"model": AuthSuccess}, 400: {"model": AuthFailed}})
async def post_login(
    request: Union[LoginRequest, dict] = Body(LoginRequest), # Union to prevent auto 422 error
):
    if isinstance(request, dict): # Validation failed
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
            content={
                "success": True,
                "redirect": "/"
            }
        )
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
    request: Union[RegisterRequest, dict] = Body(RegisterRequest), # Union to prevent auto 422 error
):
    if isinstance(request, dict): # Validation failed
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Dữ liệu không hợp lệ"
            }
        )   
    if register_user(request.full_name, request.username, request.email, request.password):
        return JSONResponse(
            content={
                "success": True,
                "redirect": "/login"
            }
        )
    else:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Tên người dùng hoặc email đã tồn tại"
            }
        )
