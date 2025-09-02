from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from database import check_login

from .utils import NO_CACHE_HEADERS

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
def get_register(request: Request):
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
    

@router.get("/admin", name="admin", response_class=HTMLResponse)
async def get_admin(request: Request):
    """Admin dashboard page - requires admin role"""
    try:
        user = await check_login(request, role="admin")
        if user.role != "admin":
            # Redirect to login với admin parameter
            return RedirectResponse(url="/login?admin=true")
    except HTTPException:
        # Redirect to login với admin parameter
        return RedirectResponse(url="/login?admin=true")
    
    response = templates.TemplateResponse(
        "admin.html",
        {"request": request, "current_user": user.to_dict()}
    )
    response.headers.update(NO_CACHE_HEADERS)
    return response

@router.get("/", name="index", response_class=HTMLResponse)
async def get_index(request: Request):
    try:
        user = await check_login(request)
        # Nếu là admin thì redirect về admin page
        if user.role == "admin":
            return RedirectResponse(url="/admin")
    except HTTPException: # Redirect to login page when user is not logged in
        return RedirectResponse(url="/login")
    response = templates.TemplateResponse(
        "index.html",
        {"request": request, "current_user": user.to_dict()}
    )
    response.headers.update(NO_CACHE_HEADERS)
    return response