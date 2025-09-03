from fastapi import APIRouter, Request, HTTPException

from database import check_login, get_user_sessions, get_session_with_messages, create_chat_session, delete_chat_session, get_chat_session
from backend.schema import ChatRequest, SessionResponse, SessionMessagesResponse, PreChatResponse
from backend.llm import ModelManager

from .utils import CommonResponse


router = APIRouter()
    
@router.post("/chat", name="chat")
async def chat(request: Request, data: ChatRequest) -> PreChatResponse:
    user = await check_login(request)
    session_id = data.session_id
    if session_id is None:
        session_id = await create_chat_session(user.id)
        if session_id is None:
            raise HTTPException(status_code=500, detail=f"Failed to create new chat session")
    model_output = await ModelManager.pre_inference(session_id, user.id, data.text, data.model_id, data.params)
    if model_output == None:
        raise HTTPException(status_code=500, detail="Failed to inference model")    
    response: PreChatResponse = {
        "session_id": session_id,
        "role": "bot",
        "web_sources": model_output["web_sources"],
        "rag_sources": model_output["rag_sources"],
        "extra_data": model_output["extra_data"],
        "result_url": model_output["result_url"]
    }    
    return response

@router.get("/sessions")
async def sessions(request: Request) -> list[SessionResponse]:
    user = await check_login(request)
    sessions = await get_user_sessions(user.id)
    return [session.to_dict() for session in sessions] #type:ignore

@router.get("/session/{session_id}/messages")
async def session_messages(request: Request, session_id: str) -> SessionMessagesResponse:
    user = await check_login(request)
    chat_session = await get_session_with_messages(session_id)
    if chat_session and chat_session.user_id == user.id:
        # Fix web_sources in messages for backward compatibility
        messages = [msg.to_dict()for msg in chat_session.messages]
        result: SessionMessagesResponse = {
            "session": chat_session.to_dict(), #type:ignore
            "messages": messages
        }
        return result
    raise HTTPException(status_code=404, detail=f"Not found session with id: {session_id}")

@router.delete("/session/{session_id}")
async def delete_session(request: Request, session_id: str):
    user = await check_login(request)
    chat_session = await get_chat_session(session_id)
    if chat_session and chat_session.user_id == user.id:
        chat_session = await delete_chat_session(chat_session)
        return CommonResponse(200, True, "Ok")
    else:
        raise HTTPException(status_code=404, detail=f"Not found session with id: {session_id}")