import os
import re
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from beanie import PydanticObjectId
from beanie.operators import Or, In
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
3. FOR BOOKING REQUESTS (e.g. "Book the home in Taharpur", "Book Saurabh's home", "Book #1"):
   - When the user explicitly wants to book or reserve a stay:
     a) If you already know the home (or only 1 home exists in that location), call createBooking immediately with the homeId/homeName, checkIn, checkOut, and guests.
     b) If you don't know which home they want, use searchHomes first to find it, or present options and ask them which one they want to book.
     c) If dates are provided, pass them to createBooking. If dates are not provided, call createBooking with flexible/default dates so the reservation is confirmed.
4. FOR CANCELLATION & REMOVING BOOKED HOMES (e.g. "Cancel my booking", "Remove the home which is booked", "Cancel reservation for Canada", "Delete my booking"):
   - When user wants to cancel or remove a reservation, call cancelBooking immediately.
   - If user asks about their current bookings ("What are my bookings?", "Show my booked stays"), call getUserBookings.
5. FOR FAVOURITES / WISHLIST (e.g. "Show my saved homes", "Add this to favourites", "Remove from favourites"):
   - Call manageFavourites with action 'list', 'add', or 'remove'.
6. When showing homes, present them in a clean numbered list with:
   - Name
   - Location
   - Price (₹/night)
   - Rating
   - ID (so the user can easily say "Book #1" or "Tell me more")
7. STRICT TRUTHFULNESS & ZERO HALLUCINATION: You must ONLY mention and describe homes that exist in HavenTo database. If a stay exists in a location (such as "Saurabh's home" in Taharpur), describe it accurately. NEVER invent fake hotels.
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
    {
        "type": "function",
        "function": {
            "name": "createBooking",
            "description": "Book or reserve a home for the user on HavenTo. Use this whenever the user wants to book or reserve a property. Can accept homeId or homeName, checkIn, checkOut, and guests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "homeId": {
                        "type": "string",
                        "description": "The MongoDB ObjectId of the home to book (preferred)",
                    },
                    "homeName": {
                        "type": "string",
                        "description": "The name of the home to book if homeId is not known",
                    },
                    "checkIn": {
                        "type": "string",
                        "description": "Check-in date (e.g. 'YYYY-MM-DD' or '2025-10-15')",
                    },
                    "checkOut": {
                        "type": "string",
                        "description": "Check-out date (e.g. 'YYYY-MM-DD' or '2025-10-20')",
                    },
                    "guests": {
                        "type": "integer",
                        "description": "Number of guests (default 1)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancelBooking",
            "description": "Cancel or remove an existing booked home or reservation. Use this whenever the user wants to cancel, remove, or delete a booking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bookingId": {
                        "type": "string",
                        "description": "The MongoDB ObjectId of the booking to cancel (if known)",
                    },
                    "homeName": {
                        "type": "string",
                        "description": "The name of the booked home to cancel (if bookingId is not known)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for cancellation (e.g. Change of plans, Found alternative, Emergency)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manageFavourites",
            "description": "Manage user's saved/favourite homes on HavenTo. Can list saved homes, add a home to favourites, or remove a home from favourites.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "add", "remove"],
                        "description": "Action: 'list' to view favourites, 'add' to save, 'remove' to remove from saved",
                    },
                    "homeId": {
                        "type": "string",
                        "description": "The MongoDB ObjectId of the home (for add or remove)",
                    },
                    "homeName": {
                        "type": "string",
                        "description": "The name of the home (if homeId is not known)",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predictDynamicPricing",
            "description": "Predict fair-market dynamic nightly price and demand drivers for any destination or property using our Machine Learning model.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City or destination (e.g. Goa, Taharpur, Mumbai, Delhi)"},
                    "category": {"type": "string", "description": "Property category (e.g. Villa, Trending, Apartment, Cabin, Beachfront)"},
                    "guests": {"type": "integer", "description": "Number of guests (e.g. 2, 4, 6)"},
                    "amenities": {"type": "array", "items": {"type": "string"}, "description": "List of amenities (e.g. WiFi, Swimming Pool, Air Conditioning)"}
                },
                "required": ["location"],
            },
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
            if not user_id or user_id == "anonymous_guest" or not PydanticObjectId.is_valid(user_id):
                return {
                    "error": "User must be logged in to view bookings.",
                    "requiresLogin": True
                }
            user_obj_id = PydanticObjectId(user_id)
            now = datetime.now(timezone.utc)
            bookings = await Booking.find(
                Or(Booking.userId == user_obj_id, Booking.user == user_obj_id)
            ).sort("-createdAt").limit(10).to_list()

            if not bookings:
                return {"count": 0, "bookings": [], "message": "You don't have any bookings yet."}

            # Auto-complete past stays
            for b in bookings:
                if b.status == "confirmed" and b.checkOut:
                    try:
                        co_dt = b.checkOut if isinstance(b.checkOut, datetime) else datetime.fromisoformat(str(b.checkOut).replace("Z", "+00:00"))
                        if co_dt.tzinfo is None:
                            co_dt = co_dt.replace(tzinfo=timezone.utc)
                        if co_dt < now:
                            b.status = "completed"
                            b.updatedAt = now
                            await b.save()
                    except Exception:
                        pass

            home_ids = [b.homeId or b.home for b in bookings if (b.homeId or b.home)]
            homes = await Home.find(In(Home.id, home_ids)).to_list() if home_ids else []
            homes_dict = {h.id: h for h in homes}

            booking_list = []
            for b in bookings:
                h = homes_dict.get(b.homeId or b.home)
                h_name = h.houseName.strip() if h else "Property details unavailable"
                h_loc = h.location.strip() if h else ""
                h_price = f"₹{h.price:,.0f}/night" if h else ""
                booking_list.append({
                    "bookingId": str(b.id),
                    "status": b.status,
                    "homeName": h_name,
                    "location": h_loc,
                    "pricePerNight": h_price,
                    "totalPrice": f"₹{b.totalPrice:,.0f}" if b.totalPrice else "",
                    "dates": f"{b.checkIn} to {b.checkOut}" if (b.checkIn and b.checkOut) else "Flexible dates",
                    "guests": b.guests
                })

            return {
                "count": len(booking_list),
                "bookings": booking_list
            }

        elif tool_name == "createBooking":
            if not user_id or user_id == "anonymous_guest" or not PydanticObjectId.is_valid(user_id):
                return {
                    "error": "User must be logged in to create a booking.",
                    "requiresLogin": True
                }

            target_home = None
            home_id_arg = args.get("homeId")
            if home_id_arg and PydanticObjectId.is_valid(home_id_arg):
                try:
                    target_home = await Home.get(PydanticObjectId(home_id_arg))
                except Exception:
                    target_home = None

            query_term = (args.get("homeName") or args.get("location") or home_id_arg or "").strip(" .,!?:;'\"")
            if not target_home and query_term:
                # 1. Try matching houseName directly
                target_home = await Home.find_one({"houseName": {"$regex": query_term, "$options": "i"}})
                # 2. If not found, try matching by location
                if not target_home:
                    loc_homes = await Home.find({"location": {"$regex": query_term, "$options": "i"}}).sort("-rating").to_list()
                    if len(loc_homes) == 1:
                        target_home = loc_homes[0]
                    elif len(loc_homes) > 1:
                        return {
                            "status": "multiple_options",
                            "message": f"I found {len(loc_homes)} stays in {query_term}. Which one would you like me to book?",
                            "options": [
                                {
                                    "id": str(h.id),
                                    "name": h.houseName.strip(),
                                    "price": f"₹{h.price:,.0f}/night",
                                    "rating": h.rating
                                }
                                for h in loc_homes
                            ]
                        }

            if not target_home:
                return {
                    "error": "Could not find the property to book. Please specify the home name or ID."
                }

            # Parse dates and calculate total price
            check_in_raw = args.get("checkIn")
            check_out_raw = args.get("checkOut")
            check_in_dt = None
            check_out_dt = None
            calculated_total = float(target_home.price)
            guests_count = int(args.get("guests", 1) or 1)

            if check_in_raw and check_out_raw:
                try:
                    ci = datetime.fromisoformat(str(check_in_raw).replace("Z", "+00:00"))
                    co = datetime.fromisoformat(str(check_out_raw).replace("Z", "+00:00"))
                    diff_days = max(1, (co.date() - ci.date()).days)
                    calculated_total = float(diff_days * target_home.price)
                    check_in_dt = ci
                    check_out_dt = co
                except Exception:
                    check_in_dt = check_in_raw
                    check_out_dt = check_out_raw

            user_obj_id = PydanticObjectId(user_id)
            home_obj_id = target_home.id

            new_booking = Booking(
                homeId=home_obj_id,
                home=home_obj_id,
                userId=user_obj_id,
                user=user_obj_id,
                checkIn=check_in_dt,
                checkOut=check_out_dt,
                totalPrice=calculated_total,
                guests=guests_count,
                status="confirmed"
            )
            await new_booking.insert()

            date_str = f"{check_in_raw} to {check_out_raw}" if (check_in_raw and check_out_raw) else "Confirmed (flexible dates)"

            return {
                "success": True,
                "bookingId": str(new_booking.id),
                "homeName": target_home.houseName.strip(),
                "location": target_home.location.strip(),
                "pricePerNight": f"₹{target_home.price:,.0f}",
                "totalPrice": f"₹{calculated_total:,.0f}",
                "dates": date_str,
                "guests": guests_count,
                "status": "confirmed",
                "message": f"Booking successfully confirmed for {target_home.houseName.strip()} in {target_home.location.strip()}!"
            }

        elif tool_name == "cancelBooking":
            if not user_id or user_id == "anonymous_guest" or not PydanticObjectId.is_valid(user_id):
                return {
                    "error": "You must be logged in to cancel or remove a booked home.",
                    "requiresLogin": True
                }

            user_obj_id = PydanticObjectId(user_id)
            booking_id = args.get("bookingId")
            home_name = (args.get("homeName") or "").strip(" .,!?:;'\"")
            reason = args.get("reason") or "Change of travel plans"
            cancel_all = bool(args.get("cancelAll")) or "all" in home_name.lower()

            now = datetime.now(timezone.utc)
            all_user_bookings = await Booking.find(
                Or(Booking.userId == user_obj_id, Booking.user == user_obj_id)
            ).sort("-createdAt").to_list()

            # 1. Automatically complete past bookings and isolate active confirmed bookings
            confirmed_bookings = []
            for b in all_user_bookings:
                if b.status == "confirmed":
                    if b.checkOut:
                        try:
                            co_dt = b.checkOut if isinstance(b.checkOut, datetime) else datetime.fromisoformat(str(b.checkOut).replace("Z", "+00:00"))
                            if co_dt.tzinfo is None:
                                co_dt = co_dt.replace(tzinfo=timezone.utc)
                            if co_dt < now:
                                b.status = "completed"
                                b.updatedAt = now
                                await b.save()
                                continue
                        except Exception:
                            pass
                    confirmed_bookings.append(b)

            if not confirmed_bookings:
                if all_user_bookings and all(b.status in ["cancelled", "completed"] for b in all_user_bookings):
                    return {
                        "error": "You don't have any active upcoming bookings to remove right now. Your past trips have already completed."
                    }
                return {
                    "error": "You do not have any active confirmed bookings to cancel or remove."
                }

            # If user wants to cancel all booked homes
            if cancel_all:
                cancelled_names = []
                for b in confirmed_bookings:
                    b.status = "cancelled"
                    b.cancellationReason = reason
                    b.cancelledAt = now
                    b.updatedAt = now
                    await b.save()
                    h = await Home.get(b.homeId or b.home) if (b.homeId or b.home) else None
                    if h:
                        cancelled_names.append(h.houseName.strip())

                names_str = ", ".join(cancelled_names) if cancelled_names else f"{len(confirmed_bookings)} properties"
                return {
                    "success": True,
                    "cancelledCount": len(confirmed_bookings),
                    "status": "cancelled",
                    "message": f"Successfully cancelled and removed {len(confirmed_bookings)} booked home(s) ({names_str}). The reserved dates have been released."
                }

            # 2. Try to match by bookingId
            target_booking = None
            if booking_id and PydanticObjectId.is_valid(booking_id):
                for b in confirmed_bookings:
                    if str(b.id) == booking_id:
                        target_booking = b
                        break

            # 3. Check number reference (e.g. "1", "#1", "Remove #1")
            num_match = re.search(r"#?(\d+)", home_name)
            if not target_booking and num_match:
                idx = int(num_match.group(1)) - 1
                if 0 <= idx < len(confirmed_bookings):
                    target_booking = confirmed_bookings[idx]

            # 4. Try to match by homeName or location flexibly
            generic_words = {"home", "booked home", "the home", "it", "this", "my booking", "stay", "booked", "unknown", "the stay", "reservation"}
            if not target_booking and home_name and home_name.lower() not in generic_words:
                home_ids = [b.homeId or b.home for b in confirmed_bookings if (b.homeId or b.home)]
                homes = await Home.find(In(Home.id, home_ids)).to_list() if home_ids else []
                homes_dict = {h.id: h for h in homes}

                lower_term = home_name.lower()
                for b in confirmed_bookings:
                    h = homes_dict.get(b.homeId or b.home)
                    if h:
                        h_name_lower = h.houseName.strip().lower()
                        h_loc_lower = h.location.strip().lower()
                        combined = f"{h_name_lower} in {h_loc_lower}"
                        if (h_name_lower in lower_term or 
                            h_loc_lower in lower_term or 
                            lower_term in h_name_lower or 
                            lower_term in h_loc_lower or 
                            lower_term in combined or 
                            combined in lower_term):
                            target_booking = b
                            break

            # 5. If only 1 confirmed booking exists, select it automatically!
            if not target_booking:
                if len(confirmed_bookings) == 1:
                    target_booking = confirmed_bookings[0]
                else:
                    home_ids = [b.homeId or b.home for b in confirmed_bookings if (b.homeId or b.home)]
                    homes = await Home.find(In(Home.id, home_ids)).to_list() if home_ids else []
                    homes_dict = {h.id: h for h in homes}
                    options = []
                    for i, b in enumerate(confirmed_bookings):
                        h = homes_dict.get(b.homeId or b.home)
                        h_loc = f" in {h.location.strip()}" if h and h.location else ""
                        options.append({
                            "number": i + 1,
                            "bookingId": str(b.id),
                            "homeName": f"{h.houseName.strip()}{h_loc}" if h else "Unknown property",
                            "dates": f"{b.checkIn} to {b.checkOut}" if (b.checkIn and b.checkOut) else "Flexible dates"
                        })
                    return {
                        "status": "multiple_bookings",
                        "message": f"You have {len(confirmed_bookings)} active confirmed bookings. Which one would you like me to remove or cancel?",
                        "options": options
                    }

            # 6. Perform cancellation
            target_booking.status = "cancelled"
            target_booking.cancellationReason = reason
            target_booking.cancelledAt = now
            target_booking.updatedAt = now
            await target_booking.save()

            target_home = await Home.get(target_booking.homeId or target_booking.home) if (target_booking.homeId or target_booking.home) else None
            h_name = target_home.houseName.strip() if target_home else "the property"
            h_loc = f" in {target_home.location.strip()}" if target_home and target_home.location else ""

            return {
                "success": True,
                "bookingId": str(target_booking.id),
                "homeName": h_name,
                "status": "cancelled",
                "message": f"Your booking for {h_name}{h_loc} has been cancelled and removed successfully. The reserved dates have been released."
            }



        elif tool_name == "manageFavourites":
            if not user_id or user_id == "anonymous_guest" or not PydanticObjectId.is_valid(user_id):
                return {
                    "error": "User must be logged in to manage favourites.",
                    "requiresLogin": True
                }

            user = await User.get(PydanticObjectId(user_id))
            if not user:
                return {"error": "User not found."}

            action = args.get("action", "list")
            user_favs = getattr(user, "favourites", []) or []

            if action == "list":
                if not user_favs:
                    return {"count": 0, "favourites": [], "message": "You have no saved favourites yet."}
                fav_homes = await Home.find({"_id": {"$in": user_favs}}).to_list()
                return {
                    "count": len(fav_homes),
                    "favourites": [
                        {
                            "id": str(h.id),
                            "name": h.houseName.strip(),
                            "location": h.location.strip(),
                            "price": f"₹{h.price:,.0f}/night",
                            "rating": h.rating
                        }
                        for h in fav_homes
                    ]
                }

            # Find target home for add or remove
            home_id_arg = args.get("homeId")
            home_name_arg = (args.get("homeName") or "").strip(" .,!?:;'\"")
            target_home = None
            if home_id_arg and PydanticObjectId.is_valid(home_id_arg):
                target_home = await Home.get(PydanticObjectId(home_id_arg))
            if not target_home and home_name_arg:
                target_home = await Home.find_one({"houseName": {"$regex": home_name_arg, "$options": "i"}})

            if not target_home:
                return {"error": "Could not find the property to update favourites."}

            if action == "add":
                if target_home.id not in user_favs:
                    user_favs.append(target_home.id)
                    user.favourites = user_favs
                    await user.save()
                return {
                    "success": True,
                    "message": f"Added {target_home.houseName.strip()} to your favourites!"
                }

            elif action == "remove":
                user_favs = [fid for fid in user_favs if fid != target_home.id]
                user.favourites = user_favs
                await user.save()
                return {
                    "success": True,
                    "message": f"Removed {target_home.houseName.strip()} from your favourites."
                }

            return {"error": f"Unknown favourites action: {action}"}

        elif tool_name == "predictDynamicPricing":
            from services.pricingService import predict_optimal_price
            loc = args.get("location", "Goa")
            cat = args.get("category", "Trending")
            gst = args.get("guests", 2)
            amen = args.get("amenities", [])
            prediction = predict_optimal_price(location=loc, category=cat, guests=gst, amenities=amen)
            return {
                "destination": loc,
                "category": cat,
                "guests": gst,
                "fairMarketRate": f"₹{prediction['recommended_price']:,.0f}/night",
                "recommendedRange": f"₹{prediction['min_competitive_price']:,.0f} - ₹{prediction['max_premium_price']:,.0f}",
                "demandTier": prediction["demand_tier"],
                "projectedOccupancy": f"{prediction['projected_occupancy_rate']}%",
                "keyDrivers": [d["factor"] + " (" + d["impact"] + ")" for d in prediction["value_drivers"]]
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
    executed_action = None
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
                    "qwen/qwen3.6-27b",
                    "openai/gpt-oss-120b",
                    "openai/gpt-oss-20b"
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

                                if tool_result.get("success"):
                                    if fn_name == "createBooking":
                                        executed_action = {"type": "OPEN_BOOKING", "data": tool_result}
                                    elif fn_name == "cancelBooking":
                                        executed_action = {"type": "CANCEL_BOOKING", "data": tool_result}
                                    elif fn_name == "manageFavourites":
                                        executed_action = {"type": "FAVOURITES_UPDATED", "data": tool_result}

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
                                    "tools": TOOLS,
                                    "tool_choice": "auto",
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

    action = executed_action
    if not action and matched_homes:
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
