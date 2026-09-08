import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status, Depends, Query, Body
from beanie import PydanticObjectId
from beanie.operators import Or, In
from models.home import Home
from models.user import User
from models.booking import Booking
from schemas.home import HomeResponse
from schemas.booking import BookingCreate, BookingResponse
from middleware.auth import get_current_user, get_current_user_optional

logger = logging.getLogger(__name__)

def serialize_home(home: Home) -> dict:
    photos = getattr(home, "photos", []) or []
    primary_photo = home.photo or (photos[0] if photos else None)
    return {
        "_id": str(home.id),
        "id": str(home.id),
        "houseName": home.houseName,
        "price": home.price,
        "location": home.location,
        "rating": home.rating,
        "photo": primary_photo,
        "photos": photos,
        "description": home.description,
        "category": home.category,
        "host": str(home.host) if home.host else None,
        "amenities": home.amenities or []
    }

def serialize_booking(booking: Booking, home: Optional[Home] = None) -> dict:
    h_id = booking.homeId or booking.home
    u_id = booking.userId or booking.user
    res = {
        "_id": str(booking.id),
        "id": str(booking.id),
        "homeId": str(h_id) if h_id else None,
        "userId": str(u_id) if u_id else None,
        "checkIn": booking.checkIn,
        "checkOut": booking.checkOut,
        "totalPrice": booking.totalPrice,
        "guests": booking.guests,
        "status": booking.status,
        "cancellationReason": getattr(booking, "cancellationReason", None),
        "cancellationDetails": getattr(booking, "cancellationDetails", None),
        "cancelledAt": booking.cancelledAt.isoformat() if getattr(booking, "cancelledAt", None) else None,
        "createdAt": booking.createdAt.isoformat() if booking.createdAt else None
    }
    if home:
        res["home"] = serialize_home(home)
    return res

async def get_homes(
    category: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_current_user_optional)
):
    query = {}
    if category and category != "All":
        query["category"] = category
        
    homes = await Home.find(query).to_list()
    serialized = [serialize_home(h) for h in homes]
    
    return {
        "success": True,
        "registeredHomes": serialized,
        "homes": serialized,
        "pageTitle": "HavenTo Homes",
        "currentPage": "Home",
        "isLoggedIn": user is not None,
        "user": {
            "_id": str(user.id),
            "id": str(user.id),
            "firstName": user.firstName,
            "lastName": user.lastName,
            "email": user.email,
            "userType": user.userType,
            "favourites": [str(fav) for fav in user.favourites]
        } if user else None
    }

async def get_home_details(home_id: str, user: Optional[User] = Depends(get_current_user_optional)):
    try:
        home = await Home.get(PydanticObjectId(home_id))
    except Exception:
        home = None
        
    if not home:
        raise HTTPException(status_code=404, detail="Home not found")
        
    return {
        "success": True,
        "home": serialize_home(home),
        "isLoggedIn": user is not None,
        "user": user
    }

async def get_favourites(user: User = Depends(get_current_user)):
    favourite_homes = []
    if user.favourites:
        homes = await Home.find(In(Home.id, user.favourites)).to_list()
        favourite_homes = [serialize_home(h) for h in homes]
        
    return {
        "success": True,
        "favouriteHomes": favourite_homes,
        "favourites": favourite_homes,
        "pageTitle": "My Favourites",
        "currentPage": "favourites",
        "isLoggedIn": True
    }

async def post_add_favourite(id: Optional[str] = Body(None, embed=True), homeId: Optional[str] = Body(None, embed=True), user: User = Depends(get_current_user)):
    target_id = id or homeId
    if not target_id:
        raise HTTPException(status_code=400, detail="homeId or id is required")
        
    obj_id = PydanticObjectId(target_id)
    if obj_id not in user.favourites:
        user.favourites.append(obj_id)
        await user.save()
        
    return {
        "success": True,
        "message": "Added to favourites"
    }

async def post_remove_favourite(home_id: str, user: User = Depends(get_current_user)):
    obj_id = PydanticObjectId(home_id)
    if obj_id in user.favourites:
        user.favourites = [fav for fav in user.favourites if fav != obj_id]
        await user.save()
        
    return {
        "success": True,
        "message": "Removed from favourites"
    }

async def get_bookings(user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    bookings = await Booking.find(
        Or(Booking.userId == user.id, Booking.user == user.id)
    ).sort("-createdAt").to_list()
    
    # Automatically complete past bookings whose checkout date has passed
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
    
    serialized_bookings = [serialize_booking(b, homes_dict.get(b.homeId or b.home)) for b in bookings]
    
    return {
        "success": True,
        "bookings": serialized_bookings
    }

async def post_create_booking(req: BookingCreate, user: User = Depends(get_current_user)):
    try:
        home = await Home.get(PydanticObjectId(req.homeId))
    except Exception:
        home = None
        
    if not home:
        raise HTTPException(status_code=404, detail="Property not found")
        
    new_booking = Booking(
        homeId=home.id,
        home=home.id,
        userId=user.id,
        user=user.id,
        checkIn=req.checkIn,
        checkOut=req.checkOut,
        totalPrice=req.totalPrice or home.price,
        guests=req.guests or 1,
        status="confirmed"
    )
    await new_booking.insert()
    
    return {
        "success": True,
        "message": "Booking confirmed",
        "booking": serialize_booking(new_booking, home)
    }

async def post_cancel_booking(booking_id: str, payload: dict = Body(default={}), user: User = Depends(get_current_user)):
    try:
        booking = await Booking.get(PydanticObjectId(booking_id))
    except Exception:
        booking = None
        
    if not booking or (booking.userId != user.id and booking.user != user.id):
        raise HTTPException(status_code=404, detail="Booking not found or unauthorized")
        
    if booking.status == "cancelled":
        raise HTTPException(status_code=400, detail="Booking already cancelled")
        
    reason = payload.get("reason", "Change of travel plans")
    reason_details = payload.get("reasonDetails", "Cancelled by guest")
    now = datetime.now(timezone.utc)

    booking.status = "cancelled"
    booking.cancellationReason = reason
    booking.cancellationDetails = reason_details
    booking.cancelledAt = now
    booking.updatedAt = now
    await booking.save()
    
    home = await Home.get(booking.homeId or booking.home) if (booking.homeId or booking.home) else None
    
    return {
        "success": True,
        "message": "Booking cancelled successfully. The dates have been released for other guests.",
        "booking": serialize_booking(booking, home)
    }

async def delete_booking(booking_id: str, user: User = Depends(get_current_user)):
    try:
        booking = await Booking.get(PydanticObjectId(booking_id))
    except Exception:
        booking = None
        
    if not booking or (booking.userId != user.id and booking.user != user.id):
        raise HTTPException(status_code=404, detail="Booking not found or unauthorized")
        
    await booking.delete()
    return {
        "success": True,
        "message": "Booking removed completely from your list."
    }

