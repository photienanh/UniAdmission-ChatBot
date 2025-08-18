from typing import Literal, TypeAlias

UserRole = Literal["user", "admin"]
ChatMessageRole = Literal["user", "bot"] # System instruction should stored per user message