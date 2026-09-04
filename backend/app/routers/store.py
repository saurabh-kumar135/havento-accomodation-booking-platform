import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Depends, Query, Body
from beanie import PydanticObjectId
from app.models.home import Home
from app.models.user import User
from app.models.booking import Booking
from app.schemas.home import HomeResponse
from app.schemas.booking import BookingCreate, BookingResponse
from app.middleware.auth_middleware import get_current_user, get_current_user_optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="", tags=["Store & Bookings"])

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
    res = {
        "_id": str(booking.id),
        "id": str(booking.id),
        "homeId": str(booking.homeId),
        "userId": str(booking.userId),
        "checkIn": booking.checkIn,
        "checkOut": booking.checkOut,
        "totalPrice": booking.totalPrice,
        "guests": booking.guests,
        "status": booking.status,
        "createdAt": booking.createdAt.isoformat() if booking.createdAt else None
    }
    if home:
        res["home"] = serialize_home(home)
    return res

@router.get("")
@router.get("/")
@router.get("/index")
@router.get("/homes")
@router.get("/homes-list")
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

@router.get("/homes/{home_id}")
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

# Favourites Endpoints
@router.get("/favourites")
async def get_favourites(user: User = Depends(get_current_user)):
    favourite_homes = []
    if user.favourites:
        homes = await Home.find({"_id": {"$in": user.favourites}}).to_list()
        favourite_homes = [serialize_home(h) for h in homes]
        
    return {
        "success": True,
        "favouriteHomes": favourite_homes,
        "favourites": favourite_homes,
        "pageTitle": "My Favourites",
        "currentPage": "favourites",
        "isLoggedIn": True
    }

@router.post("/favourites")
@router.post("/favourites/add")
async def add_to_favourites(id: Optional[str] = Body(None, embed=True), homeId: Optional[str] = Body(None, embed=True), user: User = Depends(get_current_user)):
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

@router.delete("/favourites/{home_id}")
@router.post("/favourites/remove/{home_id}")
async def remove_from_favourites(home_id: str, user: User = Depends(get_current_user)):
    obj_id = PydanticObjectId(home_id)
    if obj_id in user.favourites:
        user.favourites = [fav for fav in user.favourites if fav != obj_id]
        await user.save()
        
    return {
        "success": True,
        "message": "Removed from favourites"
    }

# Bookings Endpoints
@router.get("/bookings")
async def get_bookings(user: User = Depends(get_current_user)):
    bookings = await Booking.find(Booking.userId == user.id).sort("-createdAt").to_list()
    
    # Enrich with home details
    home_ids = [b.homeId for b in bookings]
    homes = await Home.find({"_id": {"$in": home_ids}}).to_list()
    homes_dict = {h.id: h for h in homes}
    
    serialized_bookings = [serialize_booking(b, homes_dict.get(b.homeId)) for b in bookings]
    
    return {
        "success": True,
        "bookings": serialized_bookings
    }

@router.post("/bookings")
async def create_booking(req: BookingCreate, user: User = Depends(get_current_user)):
    try:
        home = await Home.get(PydanticObjectId(req.homeId))
    except Exception:
        home = None
        
    if not home:
        raise HTTPException(status_code=404, detail="Property not found")
        
    new_booking = Booking(
        homeId=home.id,
        userId=user.id,
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

@router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(booking_id: str, payload: dict = Body(...), user: User = Depends(get_current_user)):
    try:
        booking = await Booking.get(PydanticObjectId(booking_id))
    except Exception:
        booking = None
        
    if not booking or booking.userId != user.id:
        raise HTTPException(status_code=404, detail="Booking not found or unauthorized")
        
    if booking.status == "cancelled":
        raise HTTPException(status_code=400, detail="Booking already cancelled")
        
    booking.status = "cancelled"
    booking.updatedAt = datetime.now(timezone.utc)
    await booking.save()
    
    home = await Home.get(booking.homeId)
    
    return {
        "success": True,
        "message": "Booking cancelled successfully. The dates have been released for other guests.",
        "booking": serialize_booking(booking, home)
    }

@router.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: str, user: User = Depends(get_current_user)):
    try:
        booking = await Booking.get(PydanticObjectId(booking_id))
    except Exception:
        booking = None
        
    if not booking or booking.userId != user.id:
        raise HTTPException(status_code=404, detail="Booking not found or unauthorized")
        
    await booking.delete()
    return {
        "success": True,
        "message": "Booking removed completely from your list."
    }
