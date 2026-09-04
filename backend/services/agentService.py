import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from beanie import PydanticObjectId
from config import settings
from models.home import Home
from models.booking import Booking
from models.user import User
from rag_service.memory import rag_memory_service
import httpx

logger = logging.getLogger(__name__)

# System prompt matching HavenTo specification with strict domain guardrails
SYSTEM_PROMPT = """You are HavenTo Assistant — an exclusive, professional accommodation booking and customer support assistant for the HavenTo platform.

STRICT DOMAIN GUARDRAIL & SCOPE RESTRICTION:
- You are SOLELY and EXCLUSIVELY an assistant for the HavenTo accommodation platform.
- You must ONLY answer questions directly relevant to:
  1. Finding, browsing, recommending, and booking homes/accommodations on HavenTo.
  2. HavenTo platform features: bookings, cancellations, check-in/check-out dates, pricing, guests, locations, and saved favourites.
  3. Travel inquiries directly relevant to choosing a destination or stay on HavenTo.
- If a user asks about ANY topic unrelated to HavenTo or booking stays, politely decline to answer.

OPERATIONAL RULES:
1. Always use searchHomes when a user asks for stays, recommendations, places to stay, or mentions a location, budget, or rating. Never make up fake homes.
2. For specific properties, use getHomeDetails to fetch comprehensive details.
3. FOR BOOKING REQUESTS (e.g. "Book the home in Taharpur", "Book Saurabh's home"):
   - Acknowledge that the user's explicit intent is to BOOK/RESERVE a home.
   - If you found the home, guide them to book or confirm dates and guests.
4. When showing homes, present them in a clean numbered list with:
   - Name
   - Location
   - Price (₹/night)
   - Rating
   - ID (so the user can easily say "Book #1" or "Tell me more")
5. STRICT TRUTHFULNESS & ZERO HALLUCINATION: You must ONLY mention and describe homes that exist in HavenTo database. If a stay exists in a location (such as "Saurabh's home" in Taharpur), describe it accurately. NEVER invent fake hotels.
"""

# Tool schemas for Groq LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "searchHomes",
            "description": "Search for available homes/accommodations on HavenTo. Use this whenever the user wants to find a stay by location, name, budget, or rating.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City, town, or area to search in (e.g. Taharpur, Mumbai, Goa, Manali, Canada)",
                    },
                    "maxPrice": {
                        "type": "number",
                        "description": "Maximum price per night in INR",
                    },
                    "minRating": {
                        "type": "number",
                        "description": "Minimum rating (1-10)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "getHomeDetails",
            "description": "Get full details of a specific home by its ID or house name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "homeId": {"type": "string", "description": "The MongoDB ObjectId of the home"},
                    "homeName": {"type": "string", "description": "The name of the home if ID is not known"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "getUserBookings",
            "description": "View all existing bookings for the current user.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

async def execute_tool(tool_name: str, args: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    """Executes tools by directly querying MongoDB."""
    try:
        if tool_name == "searchHomes":
            location = args.get("location", "").strip(" .,!?:;'\"")
            query: Dict[str, Any] = {}
            if location:
                query["$or"] = [
                    {"location": {"$regex": location, "$options": "i"}},
                    {"houseName": {"$regex": location, "$options": "i"}},
                    {"description": {"$regex": location, "$options": "i"}},
                ]
            if args.get("maxPrice"):
                query["price"] = {"$lte": float(args["maxPrice"])}
            if args.get("minRating"):
                query["rating"] = {"$gte": float(args["minRating"])}

            homes = await Home.find(query).sort("-rating").limit(10).to_list()
            if not homes and location:
                # Try searching with individual words if multi-word location
                words = [w for w in location.split() if len(w) >= 3]
                if words:
                    or_clauses = []
                    for w in words:
                        or_clauses.extend([
                            {"location": {"$regex": w, "$options": "i"}},
                            {"houseName": {"$regex": w, "$options": "i"}}
                        ])
                    homes = await Home.find({"$or": or_clauses}).sort("-rating").limit(10).to_list()

            if not homes:
                all_popular = await Home.find().sort("-rating").limit(4).to_list()
                return {
                    "found": 0,
                    "message": f"No homes found matching '{location}'. Here are some popular options instead.",
                    "suggestions": [
                        {
                            "id": str(h.id),
                            "name": h.houseName.strip(),
                            "price": h.price,
                            "location": h.location.strip(),
                            "rating": h.rating,
                        }
                        for h in all_popular
                    ],
                }

            return {
                "found": len(homes),
                "homes": [
                    {
                        "id": str(h.id),
                        "name": h.houseName.strip(),
                        "price": h.price,
                        "location": h.location.strip(),
                        "rating": h.rating,
                        "description": h.description or "No description provided",
                        "photo": h.photo,
                    }
                    for h in homes
                ],
            }

        elif tool_name == "getHomeDetails":
            home_id = args.get("homeId")
            home_name = args.get("homeName")
            home = None
            if home_id:
                try:
                    home = await Home.get(PydanticObjectId(home_id))
                except Exception:
                    pass
            if not home and home_name:
                home = await Home.find_one({"houseName": {"$regex": home_name.strip(), "$options": "i"}})
            if not home:
                return {"error": "Home not found."}

            return {
                "id": str(home.id),
                "name": home.houseName.strip(),
                "location": home.location.strip(),
                "price": home.price,
                "rating": home.rating,
                "description": home.description or "",
                "photos": home.photos or [home.photo],
            }

        elif tool_name == "getUserBookings":
            if not user_id:
                return {"error": "User must be logged in to view bookings."}
            bookings = await Booking.find({"user": PydanticObjectId(user_id)}).sort("-createdAt").to_list()
            return {
                "bookingsCount": len(bookings),
                "bookings": [
                    {
                        "id": str(b.id),
                        "status": b.status,
                        "checkIn": b.checkIn.isoformat() if b.checkIn else None,
                        "checkOut": b.checkOut.isoformat() if b.checkOut else None,
                        "totalPrice": b.totalPrice,
                    }
                    for b in bookings
                ],
            }

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return {"error": str(e)}

    return {"error": f"Unknown tool: {tool_name}"}


async def extract_and_presearch_homes(message: str) -> List[Dict[str, Any]]:
    """Smart keyword extraction and MongoDB pre-search to ensure no location is missed."""
    stop_words = {
        "the", "and", "for", "with", "from", "that", "this", "what", "where", "have",
        "want", "need", "like", "just", "home", "stay", "give", "find", "show", "tell",
        "about", "location", "place", "please", "some", "here", "there", "looking", "available"
    }
    raw_words = [w.strip("?,.!:;\"'") for w in message.split()]
    candidate_terms = [w for w in raw_words if len(w) >= 3 and w.lower() not in stop_words]
    
    if not candidate_terms:
        return []

    or_queries = []
    for term in candidate_terms:
        or_queries.extend([
            {"location": {"$regex": term, "$options": "i"}},
            {"houseName": {"$regex": term, "$options": "i"}},
            {"description": {"$regex": term, "$options": "i"}}
        ])

    try:
        homes = await Home.find({"$or": or_queries}).sort("-rating").limit(6).to_list()
        return [
            {
                "id": str(h.id),
                "name": h.houseName.strip(),
                "location": h.location.strip(),
                "price": h.price,
                "rating": h.rating,
                "description": h.description or ""
            }
            for h in homes
        ]
    except Exception as err:
        logger.warning(f"Pre-search error: {err}")
        return []


async def process_chat(message: str, history: List[Dict[str, Any]], user_id: Optional[str] = None) -> Dict[str, Any]:
    """Process user chat with Groq LLM, tool-calling loop, and dynamic MongoDB retrieval."""
    
    # 1. Fetch RAG memory context
    memory_ctx = ""
    if user_id:
        memory_ctx = await rag_memory_service.get_context(user_id, message)

    # 2. Smart pre-search directly in MongoDB to guarantee matching locations are found
    matched_homes = await extract_and_presearch_homes(message)
    db_context = ""
    if matched_homes:
        db_context = "\n🏡 DATABASE SEARCH RESULTS FOR THIS QUERY:\n" + "\n".join([
            f"- {h['name']} in {h['location']} at ₹{h['price']}/night (Rating: {h['rating']}⭐, ID: {h['id']}). Description: {h['description']}"
            for h in matched_homes
        ])

    effective_system_prompt = f"{SYSTEM_PROMPT}\n{memory_ctx}\n{db_context}"

    messages = [
        {"role": "system", "content": effective_system_prompt},
        *[{"role": m.get("role", "user"), "content": m.get("content", "")} for m in history[-4:]],
        {"role": "user", "content": message}
    ]

    response_text = ""
    suggested_queries = [
        "Show stays in Taharpur",
        "Best villas in Mumbai",
        "Check my active bookings"
    ]

    # 3. Call Groq API with Tool Calling Support
    if settings.GROQ_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                models_to_try = [
                    "qwen/qwen3.8-27b",
                    "openai/gpt-oss-20b",
                    "llama-3.3-70b-versatile",
                    "groq/compound"
                ]

                for model_name in models_to_try:
                    try:
                        # Initial request with tools
                        payload = {
                            "model": model_name,
                            "messages": messages,
                            "tools": TOOLS,
                            "tool_choice": "auto",
                            "temperature": 0.5,
                            "max_tokens": 800
                        }

                        res = await client.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                                "Content-Type": "application/json"
                            },
                            json=payload
                        )

                        if res.status_code != 200:
                            logger.warning(f"Model {model_name} HTTP {res.status_code}: {res.text[:120]}")
                            continue

                        data = res.json()
                        assistant_msg = data["choices"][0]["message"]
                        tool_calls = assistant_msg.get("tool_calls")

                        # Handle Tool Calls Loop
                        iterations = 0
                        while tool_calls and iterations < 3:
                            iterations += 1
                            messages.append(assistant_msg)

                            for tc in tool_calls:
                                fn_name = tc["function"]["name"]
                                try:
                                    fn_args = json.loads(tc["function"]["arguments"])
                                except Exception:
                                    fn_args = {}

                                logger.info(f"🔧 Tool invoked: {fn_name}({fn_args})")
                                tool_result = await execute_tool(fn_name, fn_args, user_id)

                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tc["id"],
                                    "content": json.dumps(tool_result)
                                })

                            # Follow-up call with tool results
                            followup_res = await client.post(
                                "https://api.groq.com/openai/v1/chat/completions",
                                headers={
                                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                                    "Content-Type": "application/json"
                                },
                                json={
                                    "model": model_name,
                                    "messages": messages,
                                    "temperature": 0.5,
                                    "max_tokens": 800
                                }
                            )

                            if followup_res.status_code == 200:
                                followup_data = followup_res.json()
                                assistant_msg = followup_data["choices"][0]["message"]
                                tool_calls = assistant_msg.get("tool_calls")
                            else:
                                break

                        response_text = assistant_msg.get("content", "").strip()
                        if response_text:
                            break

                    except Exception as err:
                        logger.warning(f"Error trying model {model_name}: {err}")

        except Exception as e:
            logger.error(f"Groq API connection failed: {e}")

    # 4. Fallback if LLM did not reply or rate limited
    if not response_text:
        if matched_homes:
            items_str = "\n".join([
                f"- **{h['name']}** in **{h['location']}** — ₹{h['price']}/night (Rating: {h['rating']}⭐)\n  {h['description']}\n  *(ID: `{h['id']}`)*"
                for h in matched_homes
            ])
            response_text = f"I found the following stay matching your request:\n\n{items_str}\n\nWould you like more details or want to book this home?"
        else:
            response_text = "Welcome to HavenTo! 🏡 I can help you search for verified vacation homes across popular destinations like Taharpur, Mumbai, Goa, and more. What location or budget are you looking for?"

    # 5. Persist to RAG memory asynchronously
    if user_id:
        try:
            await rag_memory_service.save_memory(user_id, message, response_text)
        except Exception:
            pass

    action = None
    if matched_homes:
        action = {
            "type": "SEARCH_HOMES",
            "data": {
                "count": len(matched_homes),
                "featuredHomeId": matched_homes[0]["id"]
            }
        }

    return {
        "response": response_text,
        "reply": response_text,
        "action": action,
        "suggestedQueries": suggested_queries
    }
