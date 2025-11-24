"""
Export RLHF training data from ratings and A/B preferences

Usage:
    cd /home/xoai/UniAdmission-ChatBot/app
    
    # === BEST: Export A/B preference pairs (explicit user choices) ===
    python -m database.export_rlhf_data --output ab_preferences.json --ab-preferences
    
    # === Export star-based preference pairs (inferred from ratings) ===
    python -m database.export_rlhf_data --output star_pairs.json --star-pairs
    
    # === Export all ratings (for analysis/reward model) ===
    python -m database.export_rlhf_data --output all_ratings.jsonl
    
    # === Export only high-quality (4-5 stars) ===
    python -m database.export_rlhf_data --output high_quality.jsonl --min-rating 4
    
    # === Export as JSON instead of JSONL ===
    python -m database.export_rlhf_data --output data.json --format json

Data Types:
    - A/B preferences: Most valuable for DPO training (direct user choices)
    - Star-based pairs: Inferred preferences from same query with different ratings
    - Individual ratings: Good for reward model training or analysis
"""
import asyncio
import json
import argparse
from sqlalchemy import select
from database.manager import session
from database.schema import MessageRating, ChatMessage, ChatSession, MessagePreference

async def get_rated_messages(min_rating: int = 1):
    """Get all rated bot messages with their context"""
    async with session() as ss:
        # Get all ratings with messages
        result = await ss.execute(
            select(MessageRating, ChatMessage, ChatSession)
            .join(ChatMessage, MessageRating.message_id == ChatMessage.id)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(MessageRating.rating >= min_rating)
            .order_by(MessageRating.timestamp.desc())
        )
        
        rated_data = []
        for rating, bot_msg, session_data in result:
            # Get user query (previous message)
            user_msg_result = await ss.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == bot_msg.session_id)
                .where(ChatMessage.timestamp < bot_msg.timestamp)
                .where(ChatMessage.role == "user")
                .order_by(ChatMessage.timestamp.desc())
                .limit(1)
            )
            user_msg = user_msg_result.scalar_one_or_none()
            
            # Get conversation history (last 5 messages before this)
            history_result = await ss.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == bot_msg.session_id)
                .where(ChatMessage.timestamp < bot_msg.timestamp)
                .order_by(ChatMessage.timestamp.desc())
                .limit(5)
            )
            history = list(history_result.scalars().all())
            history.reverse()  # Chronological order
            
            rated_data.append({
                # Core training data
                "message_id": bot_msg.id,
                "user_query": user_msg.text if user_msg else None,
                "bot_response": bot_msg.text,
                "rating": rating.rating,
                
                # Model & generation info
                "model_id": bot_msg.model_id,
                "generation_params": bot_msg.generation_params,
                
                # Sources used (for context)
                "web_sources": bot_msg.web_sources,
                "rag_sources": bot_msg.rag_sources,
                "extra_data": bot_msg.extra_data,
                
                # Session context
                "session_id": bot_msg.session_id,
                "conversation_history": [
                    {
                        "role": msg.role,
                        "text": msg.text,
                        "timestamp": msg.timestamp.isoformat()
                    }
                    for msg in history
                ],
                
                # Metadata
                "timestamp": bot_msg.timestamp.isoformat(),
                "rated_at": rating.timestamp.isoformat(),
                "user_id": rating.user_id
            })
        
        return rated_data

async def export_for_rlhf(output_file: str, min_rating: int = 1, format: str = "jsonl"):
    """Export rated messages to file"""
    print(f"📊 Exporting rated messages (min rating: {min_rating})...")
    
    rated_data = await get_rated_messages(min_rating)
    
    print(f"✅ Found {len(rated_data)} rated messages")
    
    if format == "jsonl":
        # JSONL format (one JSON per line) - good for streaming/large datasets
        with open(output_file, "w", encoding="utf-8") as f:
            for item in rated_data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    elif format == "json":
        # Single JSON array
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(rated_data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Exported to: {output_file}")
    
    # Print statistics
    if rated_data:
        rating_counts = {}
        model_counts = {}
        for item in rated_data:
            rating = item["rating"]
            model = item["model_id"]
            rating_counts[rating] = rating_counts.get(rating, 0) + 1
            model_counts[model] = model_counts.get(model, 0) + 1
        
        print("\n📈 Statistics:")
        print(f"  Total rated messages: {len(rated_data)}")
        print(f"  Rating distribution:")
        for rating in sorted(rating_counts.keys()):
            print(f"    {rating} stars: {rating_counts[rating]}")
        print(f"  Model distribution:")
        for model, count in sorted(model_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"    {model}: {count}")

async def export_ab_preferences(output_file: str):
    """
    Export A/B preference pairs from message_preference table
    This is the BEST data for DPO training (explicit user choices)
    """
    print("🎯 Exporting A/B preference pairs...")
    
    async with session() as ss:
        # Get all preferences with full message data
        result = await ss.execute(
            select(MessagePreference)
            .order_by(MessagePreference.timestamp.desc())
        )
        
        preferences = result.scalars().all()
        preference_data = []
        
        for pref in preferences:
            # Get original message
            original_result = await ss.execute(
                select(ChatMessage).where(ChatMessage.id == pref.original_message_id)
            )
            original_msg = original_result.scalar_one_or_none()
            
            # Get regenerated message
            regenerated_result = await ss.execute(
                select(ChatMessage).where(ChatMessage.id == pref.regenerated_message_id)
            )
            regenerated_msg = regenerated_result.scalar_one_or_none()
            
            if not (original_msg and regenerated_msg):
                continue
            
            # Determine which is preferred
            is_original_preferred = (pref.preferred_message_id == pref.original_message_id)
            
            preference_data.append({
                # DPO training format
                "query": pref.query_text,
                "chosen": original_msg.text if is_original_preferred else regenerated_msg.text,
                "rejected": regenerated_msg.text if is_original_preferred else original_msg.text,
                
                # Additional context
                "preference_id": pref.id,
                "chosen_message_id": pref.preferred_message_id,
                "rejected_message_id": pref.regenerated_message_id if is_original_preferred else pref.original_message_id,
                
                # Generation params (useful for analysis)
                "chosen_params": original_msg.generation_params if is_original_preferred else regenerated_msg.generation_params,
                "rejected_params": regenerated_msg.generation_params if is_original_preferred else original_msg.generation_params,
                
                # Sources
                "chosen_sources": {
                    "web": original_msg.web_sources if is_original_preferred else regenerated_msg.web_sources,
                    "rag": original_msg.rag_sources if is_original_preferred else regenerated_msg.rag_sources
                },
                "rejected_sources": {
                    "web": regenerated_msg.web_sources if is_original_preferred else original_msg.web_sources,
                    "rag": regenerated_msg.rag_sources if is_original_preferred else original_msg.rag_sources
                },
                
                # Metadata
                "trigger_type": pref.trigger_type,
                "user_id": pref.user_id,
                "timestamp": pref.timestamp.isoformat()
            })
        
        # Save to file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(preference_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Exported {len(preference_data)} A/B preference pairs")
        print(f"💾 Saved to: {output_file}")
        
        # Statistics
        if preference_data:
            trigger_counts = {}
            for item in preference_data:
                trigger = item["trigger_type"]
                trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
            
            print("\n📈 Statistics:")
            print(f"  Total A/B pairs: {len(preference_data)}")
            print(f"  Trigger distribution:")
            for trigger, count in trigger_counts.items():
                print(f"    {trigger}: {count}")
        
        return preference_data

async def export_star_based_pairs(output_file: str):
    """
    Export preference pairs inferred from star ratings
    Format: Same query with different responses and ratings
    Less reliable than explicit A/B choices, but still useful
    """
    print("⭐ Finding preference pairs from star ratings...")
    
    async with session() as ss:
        # Get all rated messages grouped by session
        result = await ss.execute(
            select(MessageRating, ChatMessage)
            .join(ChatMessage, MessageRating.message_id == ChatMessage.id)
            .order_by(ChatMessage.session_id, ChatMessage.timestamp)
        )
        
        # Group by query text to find similar questions
        query_responses = {}
        for rating, bot_msg in result:
            # Get user query
            user_msg_result = await ss.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == bot_msg.session_id)
                .where(ChatMessage.timestamp < bot_msg.timestamp)
                .where(ChatMessage.role == "user")
                .order_by(ChatMessage.timestamp.desc())
                .limit(1)
            )
            user_msg = user_msg_result.scalar_one_or_none()
            
            if user_msg:
                query_text = user_msg.text.strip().lower()
                if query_text not in query_responses:
                    query_responses[query_text] = []
                
                query_responses[query_text].append({
                    "query": user_msg.text,
                    "response": bot_msg.text,
                    "rating": rating.rating,
                    "model_id": bot_msg.model_id,
                    "message_id": bot_msg.id,
                    "generation_params": bot_msg.generation_params,
                    "web_sources": bot_msg.web_sources,
                    "rag_sources": bot_msg.rag_sources
                })
        
        # Create preference pairs (higher rating = preferred)
        preference_pairs = []
        for query, responses in query_responses.items():
            if len(responses) >= 2:
                # Sort by rating
                responses.sort(key=lambda x: x["rating"], reverse=True)
                
                # Create pairs: preferred (high rating) vs rejected (low rating)
                for i in range(len(responses) - 1):
                    preferred = responses[i]
                    rejected = responses[i + 1]
                    
                    if preferred["rating"] > rejected["rating"]:
                        preference_pairs.append({
                            # Core DPO data
                            "query": preferred["query"],
                            "preferred_response": preferred["response"],
                            "rejected_response": rejected["response"],
                            
                            # Ratings
                            "preferred_rating": preferred["rating"],
                            "rejected_rating": rejected["rating"],
                            "rating_delta": preferred["rating"] - rejected["rating"],
                            
                            # Model info
                            "preferred_model": preferred["model_id"],
                            "rejected_model": rejected["model_id"],
                            
                            # Generation params
                            "preferred_params": preferred["generation_params"],
                            "rejected_params": rejected["generation_params"],
                            
                            # Sources
                            "preferred_sources": {
                                "web": preferred["web_sources"],
                                "rag": preferred["rag_sources"]
                            },
                            "rejected_sources": {
                                "web": rejected["web_sources"],
                                "rag": rejected["rag_sources"]
                            },
                            
                            # Reference IDs
                            "preferred_message_id": preferred["message_id"],
                            "rejected_message_id": rejected["message_id"]
                        })
        
        # Save preference pairs
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(preference_pairs, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Found {len(preference_pairs)} preference pairs")
        print(f"💾 Exported to: {output_file}")
        
        # Statistics
        if preference_pairs:
            rating_deltas = [p["rating_delta"] for p in preference_pairs]
            avg_delta = sum(rating_deltas) / len(rating_deltas)
            
            print("\n📈 Statistics:")
            print(f"  Total pairs: {len(preference_pairs)}")
            print(f"  Avg rating delta: {avg_delta:.2f} stars")
            print(f"  Max rating delta: {max(rating_deltas)} stars")

def main():
    parser = argparse.ArgumentParser(description="Export rated messages for RLHF training")
    parser.add_argument("--output", default="rlhf_data.jsonl", help="Output file path")
    parser.add_argument("--min-rating", type=int, default=1, help="Minimum rating to export (1-5)")
    parser.add_argument("--format", choices=["json", "jsonl"], default="jsonl", help="Output format")
    parser.add_argument("--ab-preferences", action="store_true", help="Export A/B preference pairs (BEST for DPO)")
    parser.add_argument("--star-pairs", action="store_true", help="Export preference pairs inferred from star ratings")
    
    args = parser.parse_args()
    
    if args.ab_preferences:
        asyncio.run(export_ab_preferences(args.output))
    elif args.star_pairs:
        asyncio.run(export_star_based_pairs(args.output))
    else:
        asyncio.run(export_for_rlhf(args.output, args.min_rating, args.format))

if __name__ == "__main__":
    main()

