from typing import Literal

UserRole = Literal["user", "admin"]
ChatMessageRole = Literal["user", "bot"] # System instruction should stored per user message