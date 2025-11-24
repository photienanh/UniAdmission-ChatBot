from sqlalchemy import select
from database.manager import session
from database.schema import MessagePreference, ChatMessage

async def add_preference(
    user_id: str,
    query_text: str,
    original_message_id: str,
    regenerated_message_id: str,
    preferred_message_id: str,
    trigger_type: str = "low_rating"
) -> MessagePreference | None:
    """Record user preference between original and regenerated response"""
    async with session() as ss:
        # Verify messages exist
        original_result = await ss.execute(
            select(ChatMessage).where(ChatMessage.id == original_message_id)
        )
        original = original_result.scalar_one_or_none()
        
        regenerated_result = await ss.execute(
            select(ChatMessage).where(ChatMessage.id == regenerated_message_id)
        )
        regenerated = regenerated_result.scalar_one_or_none()
        
        if not original or not regenerated:
            return None
        
        # Create preference
        preference = MessagePreference(
            user_id=user_id,
            query_text=query_text,
            original_message_id=original_message_id,
            regenerated_message_id=regenerated_message_id,
            preferred_message_id=preferred_message_id,
            trigger_type=trigger_type
        )
        
        ss.add(preference)
        await ss.commit()
        await ss.refresh(preference)
        return preference

async def get_user_preferences(
    user_id: str,
    limit: int = 100
) -> list[MessagePreference]:
    """Get all preferences by a user"""
    async with session() as ss:
        result = await ss.execute(
            select(MessagePreference)
            .where(MessagePreference.user_id == user_id)
            .order_by(MessagePreference.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

