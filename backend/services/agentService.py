import os
import json
import logging
from typing import List, Dict, Any, Optional
from beanie import PydanticObjectId
from config import settings
from models.home import Home
from models.booking import Booking
from models.user import User
from rag_service.memory import rag_memory_service

logger = logging.getLogger(__name__)

# System prompt for HavenTo Travel Concierge
SYSTEM_PROMPT = """You are HavenTo AI Concierge, a warm, sophisticated, and deeply knowledgeable travel assistant for HavenTo (a luxury vacation rental platform).
You help guests discover extraordinary stays, plan dream vacations, check pricing & availability, and manage their reservations.

Key capabilities:
1. Search & Recommend: Find ideal vacation homes based on location, budget, amenities, or vibe.
2. Context Aware: You have access to the user's past search preferences and conversation history.
3. Actions: When a user expresses intent to view a home, book, or cancel, clearly provide helpful guidance and trigger appropriate actions.

Format your responses with clean Markdown, bullet points, and emojis when appropriate. Keep answers concise, inviting, and practical.
"""

async def search_homes_tool(location: Optional[str] = None, max_price: Optional[float] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search homes in the database matching criteria."""
    query = {}
    if location:
        query["location"] = {"$regex": location, "$options": "i"}
    if category and category != "All":
        query["category"] = category
    if max_price:
        query["price"] = {"$lte": max_price}
        
    homes = await Home.find(query).limit(6).to_list()
    return [
        {
            "id": str(h.id),
            "houseName": h.houseName,
            "location": h.location,
            "price": h.price,
            "rating": h.rating,
            "category": h.category,
            "description": h.description,
            "photo": h.photo
        }
        for h in homes
    ]

async def process_chat(message: str, history: List[Dict[str, Any]], user_id: Optional[str] = None) -> Dict[str, Any]:
    """Process user chat with Groq LLM and memory context."""
    # 1. Fetch RAG memory context
    memory_ctx = ""
    if user_id:
        memory_ctx = await rag_memory_service.get_context(user_id, message)
        
    # 2. Search database for relevant homes if message contains travel keywords
    found_homes = []
    lower_msg = message.lower()
    if any(k in lower_msg for k in ["beach", "villa", "mountain", "luxury", "stay", "home", "book", "find", "search", "room", "goa", "mumbai", "delhi", "manali"]):
        found_homes = await Home.find().limit(4).to_list()
        
    homes_context = ""
    if found_homes:
        homes_context = "\n🏡 CURRENT POPULAR AVAILABLE HOMES:\n" + "\n".join([
            f"- {h.houseName} in {h.location} at ₹{h.price}/night (Rating: {h.rating}⭐, ID: {h.id})"
            for h in found_homes
        ])

    prompt = f"{SYSTEM_PROMPT}\n{memory_ctx}\n{homes_context}\n\nUser Question: {message}"
    
    response_text = ""
    suggested_queries = [
        "Show beach villas in Goa",
        "Best stays under ₹5000",
        "Check my active bookings"
    ]
    
    # 3. Call Groq API
    if settings.GROQ_API_KEY:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                models_to_try = [
                    "openai/gpt-oss-20b",
                    "openai/gpt-oss-120b",
                    "qwen/qwen3.6-27b",
                    "groq/compound"
                ]
                for model_name in models_to_try:
                    res = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": model_name,
                            "messages": [
                                {"role": "system", "content": prompt},
                                *[{"role": m.get("role", "user"), "content": m.get("content", "")} for m in history[-4:]],
                                {"role": "user", "content": message}
                            ],
                            "temperature": 0.7,
                            "max_tokens": 600
                        }
                    )
                    if res.status_code == 200:
                        data = res.json()
                        response_text = data["choices"][0]["message"]["content"]
                        if response_text:
                            break
                    else:
                        logger.warning(f"Groq model {model_name} returned {res.status_code}: {res.text[:100]}")
        except Exception as e:
            logger.error(f"Groq call failed: {e}")
            
    if not response_text:
        # Fallback intelligent response
        if "book" in lower_msg:
            response_text = "I'd love to help you book a stay! You can browse our verified listings, select your check-in and check-out dates, and confirm your reservation with zero hassle. Which destination are you traveling to?"
        elif "cancel" in lower_msg:
            response_text = "To cancel a booking, go to your **Bookings** page and select **Cancel Reservation**. You can cancel up to 24 hours prior to check-in."
        else:
            response_text = f"Welcome to HavenTo! 🏡 I can help you find stunning beach villas, cozy mountain retreats, and luxury city apartments. How can I assist your travel plans today?"

    # 4. Save to RAG memory in background
    if user_id:
        await rag_memory_service.save_memory(user_id, message, response_text)
        
    action = None
    if found_homes and any(k in lower_msg for k in ["show", "find", "view", "recommend"]):
        action = {
            "type": "SEARCH_HOMES",
            "data": {
                "count": len(found_homes),
                "featuredHomeId": str(found_homes[0].id) if found_homes else None
            }
        }

    return {
        "response": response_text,
        "reply": response_text,
        "action": action,
        "suggestedQueries": suggested_queries
    }
