"""
Migration: Add message_rating table for 1-5 star ratings

Usage:
    cd /home/xoai/UniAdmission-ChatBot/app
    python -m database.migrations.add_message_rating
"""
import asyncio
from database.manager import engine
from database.schema import Base, MessageRating

async def migrate():
    print("Creating message_rating table...")
    
    async with engine.begin() as conn:
        # Create only the message_rating table
        await conn.run_sync(MessageRating.__table__.create, checkfirst=True)
    
    print("✅ Migration complete! message_rating table created.")

if __name__ == "__main__":
    asyncio.run(migrate())

