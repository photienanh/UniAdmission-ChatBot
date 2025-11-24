from sqlalchemy import select, func
from database.manager import session
from database.schema import MessageRating, ChatMessage
from datetime import datetime, timezone

async def add_message_rating(
    message_id: str,
    user_id: str,
    rating: int
) -> MessageRating | None:
    """Add or update rating for a message"""
    async with session() as ss:
        # Verify message exists
        message_result = await ss.execute(
            select(ChatMessage).where(ChatMessage.id == message_id)
        )
        message = message_result.scalar_one_or_none()
        
        if not message:
            return None
        
        # Check if rating already exists
        existing_rating_result = await ss.execute(
            select(MessageRating).where(MessageRating.message_id == message_id)
        )
        existing_rating = existing_rating_result.scalar_one_or_none()
        
        if existing_rating:
            # Update existing rating
            existing_rating.rating = rating
            existing_rating.timestamp = datetime.now(timezone.utc)
            await ss.commit()
            await ss.refresh(existing_rating)
            return existing_rating
        else:
            # Create new rating
            new_rating = MessageRating(
                message_id=message_id,
                user_id=user_id,
                rating=rating
            )
            ss.add(new_rating)
            await ss.commit()
            await ss.refresh(new_rating)
            return new_rating

async def get_message_rating(
    message_id: str
) -> MessageRating | None:
    """Get rating for a message"""
    async with session() as ss:
        result = await ss.execute(
            select(MessageRating).where(MessageRating.message_id == message_id)
        )
        return result.scalar_one_or_none()

async def get_user_ratings(
    user_id: str,
    limit: int = 100
) -> list[MessageRating]:
    """Get all ratings by a user"""
    async with session() as ss:
        result = await ss.execute(
            select(MessageRating)
            .where(MessageRating.user_id == user_id)
            .order_by(MessageRating.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

async def get_average_rating(
    model_id: str | None = None
) -> float | None:
    """Get average rating for all messages or specific model"""
    async with session() as ss:
        query = select(func.avg(MessageRating.rating))
        
        if model_id:
            query = query.join(ChatMessage).where(ChatMessage.model_id == model_id)
        
        result = await ss.execute(query)
        avg = result.scalar_one_or_none()
        return float(avg) if avg else None

