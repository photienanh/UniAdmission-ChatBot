import uuid
from typing import List
from .history_cache import Msg

async def load_history_from_db(session_id: str, max_msgs: int) -> List[Msg]:
    from database.crud.chat import get_session_with_messages
    chat_session = await get_session_with_messages(session_id)
    if not chat_session or not chat_session.messages:
        return []
    msgs = sorted(chat_session.messages, key=lambda m: m.timestamp)
    msgs = msgs[-max_msgs:]
    return [Msg(role=m.role, text=m.text, timestamp=m.timestamp) for m in msgs]

def generate_id() -> str:
    return str(uuid.uuid4())