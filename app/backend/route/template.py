from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from database import check_login

from .utils import NO_CACHE_HEADERS

# Template routes
router = APIRouter()
templates = Jinja2Templates(directory="frontend/templates")

@router.get("/login", name="login", response_class=HTMLResponse)
def get_login(request: Request):
    def get_flashed_messages():
        return request.session.pop("_messages", [])
    response = templates.TemplateResponse(
        "login.html",
        {"request": request, "get_flashed_messages": get_flashed_messages}
    )
    response.headers.update(NO_CACHE_HEADERS)
    return response

@router.get("/register", name="register", response_class=HTMLResponse)
async def get_register(request: Request):
    # Support quick registration via query parameters (GET)
    query = request.query_params
    if any(field in query for field in ("full_name", "username", "email", "password", "confirm_password")):
        required_fields = ("full_name", "username", "email", "password", "confirm_password")
        missing = [field for field in required_fields if not query.get(field)]
        if missing:
            return JSONResponse(
                {"success": False, "message": f"Thiếu thông tin: {', '.join(missing)}"},
                status_code=400,
            )
        if query.get("password") != query.get("confirm_password"):
            return JSONResponse(
                {"success": False, "message": "Mật khẩu xác nhận không khớp"},
                status_code=400,
            )
        success = await register_user(
            query.get("full_name", "").strip(),
            query.get("username", "").strip(),
            query.get("email", "").strip(),
            query.get("password", ""),
        )
        if success:
            return JSONResponse({"success": True, "message": "Đăng ký thành công"})
        return JSONResponse(
            {"success": False, "message": "Tên người dùng hoặc email đã tồn tại"},
            status_code=400,
        )
    def get_flashed_messages():
        return request.session.pop("_messages", [])
    response = templates.TemplateResponse(
        "register.html",
        {"request": request, "get_flashed_messages": get_flashed_messages}
    )
    response.headers.update(NO_CACHE_HEADERS)
    return response
    
@router.get("/delete_account", name="delete_account", response_class=HTMLResponse)
async def get_delete(request: Request):
    user = await check_login(request)
    if user.role == "user":
        response = templates.TemplateResponse(
            "delete_account.html",
            {"request": request, "current_user": user}
        )
        response.headers.update(NO_CACHE_HEADERS)
        return response
    else:
        raise HTTPException(status_code=401, detail="Admin does not allowed to delete account")
    

@router.get("/", name="index", response_class=HTMLResponse)
async def get_index(request: Request):
    try:
        user = await check_login(request)
    except HTTPException: # Redirect to login page when user is not logged in
        return RedirectResponse(url="/login")
    response = templates.TemplateResponse(
        "index.html",
        {"request": request, "current_user": user.to_dict()}
    )
    response.headers.update(NO_CACHE_HEADERS)
    return response