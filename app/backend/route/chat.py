from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import StreamingResponse
from typing import Union

from database import check_login, add_conversation, get_user_sessions, get_session_with_messages, create_chat_session, delete_chat_session, get_chat_session
from backend.schema import ChatRequest, SessionResponse, SessionMessagesResponse, PreChatResponse
from backend.llm import ModelManager

from .utils import NO_CACHE_HEADERS, get_timestamp


router = APIRouter()
    
@router.post("/chat", name="chat")
async def chat(request: Request, data: ChatRequest) -> PreChatResponse:
    user = await check_login(request)
    session_id = data.session_id
    if session_id is None:
        session_id = await create_chat_session(user.id)
        if session_id is None:
            raise HTTPException(status_code=500, detail=f"Failed to create new chat session")
    user_timestamp = get_timestamp()
    async def finish_call(text: str):
        if model_output != None:
            bot_timestamp = get_timestamp()
            user_msg_id, bot_msg_id = await add_conversation(
                user_id=user.id,
                session_id=session_id,
                user_text=data.text,
                bot_text=text,
                model_id=model_output["model_id"],
                web_sources=model_output["web_sources"],
                rag_sources=model_output["rag_sources"],
                params=data.params,
                user_timestamp=user_timestamp,
                bot_timestamp=bot_timestamp, # Does not prevent incorrect order
                user_extra_data={},
                bot_extra_data=model_output["extra_data"]
            )
    model_output = await ModelManager.pre_inference(data.text, data.model_id, data.params, finish_call)
    if model_output == None:
        raise HTTPException(status_code=500, detail="Failed to inference model")
    text = ""
    # async for chunk in llm_manager.inference(model_output["stream_id"]):
    #     text += chunk
    response: PreChatResponse = {
        "text": text,
        "stream_id": model_output["stream_id"],
        "session_id": session_id,
        "role": "bot",
        "web_sources": model_output["web_sources"],
        "rag_sources": model_output["rag_sources"],
        "extra_data": model_output["extra_data"]
    }    
    return response

@router.get("/chat/{stream_id}")
async def stream_chat(request: Request, stream_id: str):
    return StreamingResponse(ModelManager.inference(stream_id))    

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
        result: SessionMessagesResponse = {
            "session": chat_session.to_dict(), #type:ignore
            "messages": [msg.to_dict() for msg in chat_session.messages]
        }
        return result
    raise HTTPException(status_code=404, detail=f"Not found session with id: {session_id}")

@router.delete("/session/{session_id}")
async def delete_session(request: Request, session_id: str):
    user = await check_login(request)
    chat_session = await get_chat_session(session_id)
    if chat_session and chat_session.user_id == user.id:
        chat_session = await delete_chat_session(chat_session)
        return Response(status_code=200, content="OK")
    else:
        raise HTTPException(status_code=404, detail=f"Not found session with id: {session_id}")