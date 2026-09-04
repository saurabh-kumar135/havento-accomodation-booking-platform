import os
import uuid
import logging
from typing import List, Optional
from fastapi import HTTPException, status, Depends, UploadFile, File, Form
from beanie import PydanticObjectId
import aiofiles
from config import settings
from models.home import Home
from models.user import User
from models.booking import Booking
from middleware.auth import get_current_user
from controllers.storeController import serialize_home, serialize_booking

logger = logging.getLogger(__name__)

async def get_host_homes(user: User = Depends(get_current_user)):
    homes = await Home.find(Home.host == user.id).to_list()
    serialized = [serialize_home(h) for h in homes]
    return {
        "success": True,
        "registeredHomes": serialized,
        "homes": serialized
    }

async def post_add_home(
    houseName: str = Form(...),
    price: float = Form(...),
    location: str = Form(...),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form("Trending"),
    rating: Optional[float] = Form(4.8),
    amenities: Optional[str] = Form(""),
    photos: Optional[List[UploadFile]] = File(None),
    user: User = Depends(get_current_user)
):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    saved_photos = []
    
    if photos:
        for photo in photos:
            if photo.filename:
                ext = os.path.splitext(photo.filename)[1] or ".jpg"
                filename = f"{uuid.uuid4().hex}{ext}"
                filepath = os.path.join(settings.UPLOAD_DIR, filename)
                
                async with aiofiles.open(filepath, 'wb') as out_file:
                    content = await photo.read()
                    await out_file.write(content)
                    
                saved_photos.append(f"/uploads/{filename}")
                
    photo_url = saved_photos[0] if saved_photos else "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80"
    
    amenities_list = [a.strip() for a in amenities.split(",") if a.strip()] if amenities else []
    
    new_home = Home(
        houseName=houseName,
        price=price,
        location=location,
        description=description,
        category=category or "Trending",
        rating=rating or 4.8,
        photo=photo_url,
        photos=saved_photos if saved_photos else [photo_url],
        host=user.id,
        amenities=amenities_list
    )
    await new_home.insert()
    
    if user.userType != "host":
        user.userType = "host"
        await user.save()
        
    return {
        "success": True,
        "message": "Home added successfully",
        "home": serialize_home(new_home)
    }

async def post_edit_home(
    home_id: Optional[str] = None,
    id: Optional[str] = Form(None),
    houseName: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    location: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    amenities: Optional[str] = Form(None),
    photos: Optional[List[UploadFile]] = File(None),
    user: User = Depends(get_current_user)
):
    target_id = home_id or id
    if not target_id:
        raise HTTPException(status_code=400, detail="Home ID is required")
        
    try:
        home = await Home.get(PydanticObjectId(target_id))
    except Exception:
        home = None
        
    if not home:
        raise HTTPException(status_code=404, detail="Home not found")
        
    if houseName: home.houseName = houseName
    if price: home.price = price
    if location: home.location = location
    if description: home.description = description
    if category: home.category = category
    if amenities is not None:
        home.amenities = [a.strip() for a in amenities.split(",") if a.strip()]
        
    if photos and len(photos) > 0 and photos[0].filename:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        photo = photos[0]
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(settings.UPLOAD_DIR, filename)
        async with aiofiles.open(filepath, 'wb') as out_file:
            content = await photo.read()
            await out_file.write(content)
        home.photo = f"/uploads/{filename}"
        if hasattr(home, "photos"):
            home.photos = [f"/uploads/{filename}"]
        
    await home.save()
    
    return {
        "success": True,
        "message": "Home updated successfully",
        "home": serialize_home(home)
    }

async def delete_home(home_id: str, user: User = Depends(get_current_user)):
    try:
        home = await Home.get(PydanticObjectId(home_id))
    except Exception:
        home = None
        
    if not home:
        raise HTTPException(status_code=404, detail="Home not found")
        
    await home.delete()
    return {
        "success": True,
        "message": "Home deleted successfully"
    }

async def get_host_bookings(user: User = Depends(get_current_user)):
    homes = await Home.find(Home.host == user.id).to_list()
    home_ids = [h.id for h in homes]
    homes_dict = {h.id: h for h in homes}
    
    bookings = await Booking.find({"homeId": {"$in": home_ids}}).sort("-createdAt").to_list()
    serialized = [serialize_booking(b, homes_dict.get(b.homeId)) for b in bookings]
    
    return {
        "success": True,
        "bookings": serialized
    }
