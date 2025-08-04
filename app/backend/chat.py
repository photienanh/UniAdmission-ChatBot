from fastapi import APIRouter, Request, Body, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Union, cast, Any
from datetime import datetime, timezone
from llm import ask_llm
from .database import (
    check_login, create_chat_session, get_chat_session, create_message, 
    get_user_sessions, get_session_messages, DBSession
)
from .schema import (
    SuccessResponse, ErrorReponse, FailedResponse, ServerError, NO_CACHE_HEADERS,
    ChatRequest, ChatResponse, 
    SessionResponse, SessionMessagesResponse, CreateChatSessionRequest
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", name="index", response_class=HTMLResponse)
def get_index(request: Request):
    try:
        user = check_login(request)
    except HTTPException: # Redirect to login page when user is not logged in
        return RedirectResponse(url="/login")
    response = templates.TemplateResponse(
        "index.html", 
        {"request": request, "current_user": user.to_dict()}
    )
    response.headers.update(NO_CACHE_HEADERS)
    return response
@router.post("/", name="index", response_class=HTMLResponse)
def post_index(request: Request):
    return get_index(request)
@router.get("/home", name="home", response_class=HTMLResponse)
def get_home(request: Request):
    return get_index(request)
@router.post("/chat", name="chat", response_class=JSONResponse)
async def post_chat(request: Request, data: Union[ChatRequest, dict] = Body(ChatRequest)) -> ChatResponse | Any:
    if isinstance(data, dict): return FailedResponse("Dữ liệu không hợp lệ")
    user = check_login(request)
    session_id: str | None = data.session_id
    # Tạo session mới nếu chưa có
    if session_id == None:
        chat_session = create_chat_session(user.id)
        session_id = chat_session.id
    else:
        chat_session = get_chat_session(session_id)
        if not chat_session or cast(str, chat_session.user_id) != user.id:
            data.session_id = ""
            return ErrorReponse(403, "Session không hợp lệ")
    session_id = cast(str, session_id)
    # Lưu tin nhắn của user
    user_message = create_message(session_id, 'user', data.message, [], [])
    try:
        bot_response = await ask_llm(
            question=data.message,
            session_id=session_id,
            model_type=data.model_type,
            use_web_search=data.use_web_search,
            max_results=data.search_results_count,
            priority_domains=data.priority_domains
        )
        bot_message = create_message(session_id, 'bot', bot_response['response'], bot_response["sources"], bot_response["search_sources"])
        chat_session.updated_at = datetime.now(timezone.utc)
        chat_session.auto_set_title()
        DBSession.commit()
        response = ChatResponse(
            session_id=session_id,
            message_id=bot_message.id,
            response=bot_response["response"],
            sources=bot_response["sources"],
            search_sources=bot_response["search_sources"],
        )
        return response
    except Exception as e:
        print(f"Error: {e}")
        DBSession.rollback()
        return ErrorReponse(500, f"Lỗi xử lý: {str(e)}")
    
@router.get("/sessions")
def get_sessions(request: Request) -> list[SessionResponse]:
    """Lấy danh sách phiên chat của user"""
    user = check_login(request)
    sessions = get_user_sessions(user.id, False)
    return [session.to_dict() for session in sessions] #type:ignore

@router.get("/sessions/{session_id}/messages")
def get_message(request: Request, session_id: str) -> SessionMessagesResponse:
    """Lấy tin nhắn của một phiên chat"""
    user = check_login(request)
    chat_session, messages = get_session_messages(session_id, user.id)
    return JSONResponse(content={
        "session": chat_session.to_dict(),
        "messages": [message.to_dict() for message in messages] 
    }) #type:ignore
    
@router.delete("/sessions/{session_id}")
def delete_session(request: Request, session_id: str):
    """Xóa một phiên chat"""
    user = check_login(request)
    chat_session = get_chat_session(session_id)
    if not chat_session or chat_session.user_id != user.id:
        return ErrorReponse(404, "Session không hợp lệ")
    DBSession.session.delete(chat_session)
    DBSession.commit()
    return SuccessResponse("Xóa phiên chat thành công")

@router.post("/sessions")
def create_session(request: Request, data: CreateChatSessionRequest) -> SessionResponse:
    """Tạo phiên chat mới"""
    user = check_login(request)
    chat_session = create_chat_session(user.id, title=data.title)
    return chat_session.to_dict() #type:ignore