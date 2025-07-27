from fastapi import APIRouter, Request, Body, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Union, cast, Any
from datetime import datetime, timezone
from .database import (
    check_login, create_chat_session, get_chat_session, create_message, 
    get_user_sessions, get_session_messages, DBSession
)
from .schema import (
    ChatRequest, ChatResponse, 
    SessionResponse, SessionMessagesResponse, CreateChatSessionRequest
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def ask_llm(question, model, retriever, session_id=None, use_custom_llm=False, use_web_search=True) -> dict[str, Any]:
    """Hàm chung để gọi LLM - Gemini hoặc Custom LLM"""
    return {"response": f"bot: {question}"}

@router.get("/", name="index", response_class=HTMLResponse)
def get_index(request: Request):
    try:
        user = check_login(request)
    except HTTPException:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("index.html", {"request": request, "current_user": user.to_dict()})
@router.get("/home", name="home", response_class=HTMLResponse)
def get_home(request: Request):
    return get_index(request)
@router.post("/chat", name="chat", response_class=JSONResponse)
async def post_chat(request: Request, data: Union[ChatRequest, dict] = Body(ChatRequest)):
    if isinstance(data, dict): # Validation failed
        raise HTTPException(status_code=400, detail="Dữ liệu không hợp lệ")
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
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Session không hợp lệ"
                }
            )
    session_id = cast(str, session_id)
    # Lưu tin nhắn của user
    user_message = create_message(
        session_id=session_id,
        sender='user',
        content=data.message
    )
    try:
        bot_response = ask_llm(
            question=data.message,
            model="gemini",
            retriever="",
            session_id=session_id,
            use_custom_llm=data.use_custom_llm,
            use_web_search=data.use_web_search
        )
        bot_message = create_message(
            session_id=session_id,
            sender='bot',
            content=bot_response['response']
        )
        # Cập nhật thời gian session
        chat_session.updated_at = datetime.now(timezone.utc)
        # Tự động tạo title cho session từ tin nhắn đầu tiên
        if not chat_session.title:
            message = data.message[:50]
            chat_session.title = message + "..." if len(message) > 50 else message
        DBSession.commit()
        response = ChatResponse(
            response=bot_response["response"],
            session_id=session_id,
            message_id=bot_message.id
        )
        return response
        
    except Exception as e:
        DBSession.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "errof": f"Lỗi xử lý: {str(e)}"
            }
        )
    
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
        return HTTPException(
            status_code=404,
            detail="Session không hợp lệ"
        )
    DBSession.session.delete(chat_session)
    DBSession.commit()
    return JSONResponse({
        "success": True
    })
    
@router.post("/sessions")
def create_session(request: Request, data: CreateChatSessionRequest) -> SessionResponse:
    """Tạo phiên chat mới"""
    user = check_login(request)
    chat_session = create_chat_session(user.id, title=data.title)
    return chat_session.to_dict() #type:ignore