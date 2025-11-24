from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from database import check_login, get_user_sessions, get_session_with_messages, create_chat_session, delete_chat_session, get_chat_session, add_message_rating, get_message_rating, add_preference, get_message
from backend.schema import ChatRequest, SessionResponse, SessionMessagesResponse, PreChatResponse
from backend.llm import ModelManager

from .utils import CommonResponse


router = APIRouter()
    
@router.post("/chat", name="chat")
async def chat(request: Request, data: ChatRequest) -> PreChatResponse:
    """
    Chat route.\n
    This would send a `PreChatResponse` first, which contain `WebSource`, `RagSource`, ...\n
    Then send access answer through `result_url` field.\n
    Result would be stored with a call from worker (See `worker_router`).\n
    Would need server to call `pre_inference` in worker, so we could prevent direct `pre_inference` request from unauthozied user, create new `ChatSession`,  provide chat history, ...
    """
    user = await check_login(request)
    session_id = data.session_id
    if session_id is None:
        session_id = await create_chat_session(user.id)
        if session_id is None:
            raise HTTPException(status_code=500, detail=f"Failed to create new chat session")
    model_output = await ModelManager.pre_inference(session_id, user.id, data.text, data.params)
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
    """Get list of `ChatSession`"""
    user = await check_login(request)
    sessions = await get_user_sessions(user.id)
    return [session.to_dict() for session in sessions] #type:ignore

@router.get("/session/{session_id}/messages")
async def session_messages(request: Request, session_id: str) -> SessionMessagesResponse:
    """Get all `ChatMessage` inside a `ChatSession`"""
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
    """Delete a `ChatSession`"""
    user = await check_login(request)
    chat_session = await get_chat_session(session_id)
    if chat_session and chat_session.user_id == user.id:
        chat_session = await delete_chat_session(chat_session)
        return CommonResponse(200, True, "Ok")
    else:
        raise HTTPException(status_code=404, detail=f"Not found session with id: {session_id}")

class RatingRequest(BaseModel):
    rating: int

@router.post("/message/{message_id}/rate")
async def rate_message(request: Request, message_id: str, data: RatingRequest):
    """Rate a bot message (1-5 stars)"""
    user = await check_login(request)
    
    # Validate rating
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Add/update rating
    rating = await add_message_rating(message_id, user.id, data.rating)
    
    if rating is None:
        raise HTTPException(status_code=404, detail=f"Message not found: {message_id}")
    
    return CommonResponse(200, True, "Rating saved successfully")

@router.get("/message/{message_id}/rating")
async def get_rating(request: Request, message_id: str):
    """Get rating for a message"""
    user = await check_login(request)
    rating = await get_message_rating(message_id)
    
    if rating:
        return rating.to_dict()
    else:
        return None

@router.get("/session/{session_id}/latest_bot_message")
async def get_latest_bot_message(request: Request, session_id: str):
    """Get latest bot message ID for rating"""
    user = await check_login(request)
    chat_session = await get_session_with_messages(session_id)
    
    if not chat_session or chat_session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Find latest bot message
    bot_messages = [msg for msg in chat_session.messages if msg.role == "bot"]
    if bot_messages:
        latest = bot_messages[-1]
        return {"message_id": latest.id}
    
    return {"message_id": None}

@router.post("/message/{message_id}/regenerate")
async def regenerate_response(request: Request, message_id: str):
    """
    Regenerate response with different temperature
    Triggered when user rates <= 3 stars
    """
    user = await check_login(request)
    
    # Get original message
    original_msg = await get_message(message_id)
    if not original_msg:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Get session
    chat_session = await get_session_with_messages(original_msg.session_id)
    if not chat_session or chat_session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Find user query (message before bot response)
    messages = chat_session.messages
    msg_index = next((i for i, m in enumerate(messages) if m.id == message_id), -1)
    
    if msg_index <= 0:
        raise HTTPException(status_code=400, detail="Cannot find user query")
    
    user_query = messages[msg_index - 1]
    
    # Change temperature for variety
    new_params = original_msg.generation_params.copy()
    old_temp = new_params.get("temperature", 0.7)
    new_params["temperature"] = 0.8 if old_temp < 0.7 else 0.5
    
    # Generate new response
    model_output = await ModelManager.pre_inference(
        session_id=original_msg.session_id,
        user_id=user.id,
        text=user_query.text,
        params=new_params
    )
    
    if not model_output:
        raise HTTPException(status_code=500, detail="Failed to regenerate")
    
    return {
        "original_message_id": message_id,
        "result_url": model_output["result_url"],
        "query_text": user_query.text,
        "variation": {
            "old_temperature": old_temp,
            "new_temperature": new_params["temperature"]
        }
    }

class PreferenceRequest(BaseModel):
    query_text: str
    original_message_id: str
    regenerated_message_id: str
    preferred_message_id: str

@router.post("/preference/submit")
async def submit_preference(request: Request, data: PreferenceRequest):
    """Submit A/B preference after comparison"""
    user = await check_login(request)
    
    # Validate
    if data.preferred_message_id not in [data.original_message_id, data.regenerated_message_id]:
        raise HTTPException(status_code=400, detail="preferred_message_id must be one of the compared messages")
    
    # Save preference
    preference = await add_preference(
        user_id=user.id,
        query_text=data.query_text,
        original_message_id=data.original_message_id,
        regenerated_message_id=data.regenerated_message_id,
        preferred_message_id=data.preferred_message_id,
        trigger_type="low_rating"
    )
    
    if not preference:
        raise HTTPException(status_code=404, detail="Messages not found")
    
    return CommonResponse(200, True, "Preference saved successfully")