from datetime import datetime, timezone

from core import ModelInfo, GenerationParams, ModelPreOutput, ModelOutput, ChatMessage
from database import add_conversation, get_session_with_messages

from .utils import generate_id
from .worker import WorkerManager

class ModelManager: # Stateless :Đ
    @classmethod
    async def pre_inference(cls, session_id: str, user_id: str, text: str, model_id: str, params: GenerationParams) -> ModelPreOutput | None:
        """Auto select suitable worker according to model id and return `ModelPreOutput`. Return `None` when failed."""
        # Performance can worry later
        session = await get_session_with_messages(session_id)
        if session is None: raise Exception("Unknown error while pre inference")
        messages_history = session.messages[-params.get("max_history", 5):]
        history: list[ChatMessage] = [message.to_dict() for message in messages_history] #type:ignore
        job_id = generate_id()
        result = await WorkerManager.pre_inference(
            user_id=user_id,
            stream_id=job_id,
            text=text,
            model_id=model_id,
            history=history,
            params=params   
        )
        return result
    @classmethod
    async def get_models(cls) -> list[ModelInfo]:
        return await WorkerManager.get_models()
    @classmethod
    async def store_chat(cls, user_id: str, session_id: str, user_text: str, user_timestamp: datetime, model_output: ModelOutput):
        """
        Update chat on database. Call in worker router only. \n
        Should be used when worker finish inference on their server, then send request to this server to store in database.
        """
        bot_timestamp = datetime.now(timezone.utc)
        user_msg_id, bot_msg_id = await add_conversation(
            user_id=user_id,
            session_id=session_id,
            user_text=user_text,
            user_summary=model_output["user_summary"],
            user_keywords=model_output["user_keywords"],
            user_intent=model_output["user_intent"],
            bot_text=model_output["text"],
            bot_summary=model_output["bot_summary"],
            bot_keywords=model_output["bot_keywords"],
            answer_state=model_output["answer_state"],
            model_id=model_output["model_id"],
            web_sources=model_output["web_sources"],
            rag_sources=model_output["rag_sources"],
            params=model_output["generation_params"],
            user_timestamp=user_timestamp,
            bot_timestamp=bot_timestamp, # Does not prevent incorrect order
            user_extra_data={},
            bot_extra_data=model_output["extra_data"]
        )