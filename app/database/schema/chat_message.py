from core.types import ChatMessageRole, AnswerState, WebSource, RagSource, GenerationParams
from .base import *

class ChatMessage(Base): #type:ignore
    __tablename__ = "chat_message"
    
    id = cast(str, Column(String(36), primary_key=True, default=generate_id))
    session_id = cast(str, Column(String(36), ForeignKey("chat_session.id"), nullable=False))
    role = cast(ChatMessageRole, Column(String(10), nullable=False))
    text = cast(str, Column(Text, nullable=False))
    
    # For multi turn
    summary = cast(str, Column(Text, nullable=False)) # Message summary
    user_intent = cast(Optional[str], Column(Text)) # User intent
    answer_state = cast(Optional[AnswerState], Column(Text)) # Bot answer status [clarification_needed, answer_successfully, answer_related, not_found, off_topic]
    keywords = cast(list[str], Column(JSON, nullable=False)) # Entity listed in message
    # End
    timestamp = cast(datetime, Column(DateTime, default=datetime_now))
    
    model_id = cast(str, Column(Text, nullable=False)) # user message should have model id too
    web_sources = cast(Optional[list[WebSource]], Column(JSON))
    rag_sources = cast(Optional[list[RagSource]], Column(JSON))
    generation_params = cast(GenerationParams, Column(JSON, nullable=False)) # user message should have generation params too

    extra_data = cast(dict[str, Any], Column(JSON, default=extra_data)) # System instruction, query, hyde, ...
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "text": self.text,
            "timestamp": self.timestamp.isoformat(),
            "model_id": self.model_id,
            "rag_sources": self.rag_sources,
            "web_sources": self.web_sources,
            "generation_params": self.generation_params,
            "extra_data": self.extra_data,
            "summary": self.summary,
            "user_intent": self.user_intent,
            "answer_state": self.answer_state,
            "keywords": self.keywords,
        }