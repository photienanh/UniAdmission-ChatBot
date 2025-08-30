import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Literal

Role = Literal["user", "bot", "assistant", "model"]

MAX_HISTORY_MSGS = 12          # chỉ giữ N message gần nhất
TTL_SECONDS      = 900         # cache sống 15 phút không hoạt động

@dataclass
class Msg:
    role: str
    text: str

@dataclass
class Entry:
    messages: List[Msg] = field(default_factory=list)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

_cache: Dict[str, Entry] = {}

def _now():
    return datetime.now(timezone.utc)

def _expired(entry: Entry) -> bool:
    return (_now() - entry.updated_at) > timedelta(seconds=TTL_SECONDS)

async def get_history(session_id: str, loader):
    """
    Trả về danh sách Msg cho session_id.
    loader: async fn(session_id, max_msgs) -> List[Msg]  (đã sort tăng dần, đã limit)
    """
    entry = _cache.get(session_id)
    # if entry and not _expired(entry):
    #     return entry.messages
    entry = None # Force reload messages
    # cache miss hoặc hết hạn → load từ DB
    if not entry:
        entry = Entry()
        _cache[session_id] = entry

    async with entry.lock:
        if entry.messages and not _expired(entry):
            return entry.messages  # double-check sau khi acquire lock
        msgs = await loader(session_id, MAX_HISTORY_MSGS)
        entry.messages = msgs[-MAX_HISTORY_MSGS:]
        entry.updated_at = _now()
        return entry.messages

async def append_user_and_bot(session_id: str, user_msg: Msg, bot_msg: Msg | None):
    entry = _cache.get(session_id)
    if not entry:
        entry = Entry()
        _cache[session_id] = entry
    async with entry.lock:
        if user_msg:
            entry.messages.append(user_msg)
        if bot_msg:
            entry.messages.append(bot_msg)
        # giữ N cuối cùng
        if len(entry.messages) > MAX_HISTORY_MSGS:
            entry.messages = entry.messages[-MAX_HISTORY_MSGS:]
        entry.updated_at = _now()

async def invalidate(session_id: str):
    _cache.pop(session_id, None)

async def invalidate_all():
    _cache.clear()
