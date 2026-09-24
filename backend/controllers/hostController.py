import os
import uuid
import logging
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi import HTTPException, status, Depends, UploadFile, File, Form
from beanie import PydanticObjectId
from beanie.operators import Or, In
import aiofiles
from config import settings
from models.home import Home
from models.user import User, HostKyc
from models.booking import Booking
from middleware.auth import get_current_user, get_current_user_optional
from controllers.storeController import serialize_home, serialize_booking
from services.kycService import verify_host_identity

logger = logging.getLogger(__name__)

async def get_host_homes(user: User = Depends(get_current_user)):
    homes = await Home.find(Home.host == user.id).to_list()
    serialized = [serialize_home(h) for h in homes]
    return {
        "success": True,
        "registeredHomes": serialized,
        "homes": serialized
    }

async def get_add_home(user: User = Depends(get_current_user)):
    return {
        "success": True,
        "pageTitle": "Add Home to HavenTo",
        "currentPage": "addHome",
        "editing": False,
        "isLoggedIn": True,
        "user": user.email if user else None
    }

async def get_edit_home(home_id: str, user: User = Depends(get_current_user)):
    try:
        home = await Home.get(PydanticObjectId(home_id))
    except Exception:
        home = None
    if not home:
        raise HTTPException(status_code=404, detail="Home not found")
    return {
        "success": True,
        "home": serialize_home(home),
        "editing": True,
        "isLoggedIn": True
    }

async def post_add_home(
    houseName: str = Form(...),
    price: float = Form(...),
    location: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form("Trending"),
    rating: Optional[float] = Form(4.8),
    amenities: Optional[str] = Form(""),
    photos: Optional[List[UploadFile]] = File(None),
    user: User = Depends(get_current_user)
):
    if not user.hostKyc or not user.hostKyc.isVerified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "success": False,
                "requireKyc": True,
                "message": "Host identity verification required. Please verify your Aadhaar or PAN card before listing a property."
            }
        )

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
        latitude=latitude,
        longitude=longitude,
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
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
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
    if latitude is not None: home.latitude = latitude
    if longitude is not None: home.longitude = longitude
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

class KycVerificationRequest(BaseModel):
    documentType: str
    documentNumber: str
    fullName: str

async def post_verify_kyc(req: KycVerificationRequest, user: User = Depends(get_current_user)):
    verification = await verify_host_identity(
        document_type=req.documentType,
        document_number=req.documentNumber,
        full_name=req.fullName
    )
    if not verification.get("success"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=verification.get("error", "Verification failed.")
        )
    
    doc_num = verification.get("document_number")
    is_aadhaar = verification.get("document_type") == "aadhaar"
    
    if is_aadhaar and doc_num:
        user.aadharNumber = doc_num
        user.aadhaarNumber = doc_num

    user.hostKyc = HostKyc(
        isVerified=True,
        documentType=verification["document_type"],
        documentNumber=doc_num,
        aadharNumber=doc_num if is_aadhaar else None,
        aadhaarNumber=doc_num if is_aadhaar else None,
        maskedNumber=verification["masked_number"],
        documentHash=verification["document_hash"],
        fullNameAsOnDoc=verification["full_name_as_on_doc"],
        status="verified",
        verificationRef=verification["verification_ref"],
        verifiedAt=verification["verified_at"]
    )
    user.userType = "host"
    await user.save()

    return {
        "success": True,
        "message": f"{verification['document_type'].upper()} verified successfully! You are now a Verified Host on HavenTo.",
        "hostKyc": user.hostKyc.model_dump(),
        "userType": user.userType
    }

async def get_kyc_status(user: User = Depends(get_current_user)):
    return {
        "success": True,
        "hostKyc": user.hostKyc.model_dump() if user.hostKyc else {"isVerified": False, "status": "unverified"},
        "userType": user.userType
    }

async def get_host_wealth_analytics(user: Optional[User] = Depends(get_current_user_optional)):
    user_homes = []
    if user:
        try:
            from bson.objectid import ObjectId
            u_oid = ObjectId(str(user.id))
            user_homes = await Home.find(Or(Home.host == user.id, Home.host == u_oid)).to_list()
        except Exception:
            user_homes = await Home.find(Home.host == user.id).to_list()
            
    is_demo = len(user_homes) == 0
    all_homes = await Home.find().limit(6).to_list()
    target_homes = user_homes if user_homes else all_homes
    target_ids_set = {str(h.id) for h in target_homes}
    
    all_bookings = await Booking.find().sort("-createdAt").to_list()
    relevant_bookings = [
        b for b in all_bookings
        if str(getattr(b, "home", "") or getattr(b, "homeId", "") or "") in target_ids_set
    ]
    confirmed_bookings = [b for b in relevant_bookings if b.status != "cancelled"]
    
    # Pre-fetch guest users for displaying real guest names
    guest_uids = []
    for b in confirmed_bookings:
        u_val = getattr(b, "user", None) or getattr(b, "userId", None)
        if u_val:
            guest_uids.append(u_val)
    guest_map = {}
    if guest_uids:
        try:
            guest_users = await User.find(In(User.id, guest_uids)).to_list()
            for gu in guest_users:
                g_name = f"{gu.firstName} {gu.lastName}".strip() or gu.email
                guest_map[str(gu.id)] = g_name
        except Exception:
            pass

    homes_dict = {str(h.id): h for h in target_homes}
    
    total_gross = 0.0
    total_nights = 0
    serialized_bookings = []
    
    for b in confirmed_bookings:
        h_key = str(getattr(b, "home", "") or getattr(b, "homeId", "") or "")
        h = homes_dict.get(h_key)
        price_per_night = float(h.price) if h and hasattr(h, "price") else 5000.0
        
        nights = 2
        if b.checkIn and b.checkOut:
            try:
                cin = b.checkIn if isinstance(b.checkIn, datetime) else datetime.fromisoformat(str(b.checkIn).replace('Z', '+00:00'))
                cout = b.checkOut if isinstance(b.checkOut, datetime) else datetime.fromisoformat(str(b.checkOut).replace('Z', '+00:00'))
                diff = (cout - cin).days
                if diff > 0:
                    nights = diff
            except Exception:
                nights = 2
                
        booking_revenue = float(b.totalPrice or 0.0)
        if booking_revenue <= 0.0:
            booking_revenue = price_per_night * nights
            
        total_gross += booking_revenue
        total_nights += nights
        
        b_user_key = str(getattr(b, "user", "") or getattr(b, "userId", "") or "")
        guest_name = guest_map.get(b_user_key, "Guest")
        
        cin_str = str(b.checkIn).split("T")[0] if b.checkIn else ""
        cout_str = str(b.checkOut).split("T")[0] if b.checkOut else ""
        
        serialized_bookings.append({
            "id": str(b.id),
            "homeId": h_key,
            "houseName": h.houseName if h else "Haven Property",
            "location": h.location if h else "India",
            "nights": nights,
            "guests": getattr(b, "guests", 1),
            "guestName": guest_name,
            "checkIn": cin_str,
            "checkOut": cout_str,
            "totalPrice": booking_revenue,
            "netPayout": round(booking_revenue * 0.97, 0),
            "status": b.status,
            "createdAt": b.createdAt.isoformat() if hasattr(b.createdAt, "isoformat") else str(b.createdAt)
        })
        
    platform_fee_percent = 3
    net_payout = round(total_gross * (1.0 - platform_fee_percent / 100.0), 0)
    avg_stay = round(total_nights / max(1, len(confirmed_bookings)), 1)
    avg_val = round(total_gross / max(1, len(confirmed_bookings)), 0)
    
    homes_breakdown = []
    for h in target_homes:
        h_bookings = [
            b for b in confirmed_bookings
            if str(getattr(b, "home", "") or getattr(b, "homeId", "") or "") == str(h.id)
        ]
        h_revenue = 0.0
        h_nights = 0
        for b in h_bookings:
            nights = 2
            if b.checkIn and b.checkOut:
                try:
                    cin = b.checkIn if isinstance(b.checkIn, datetime) else datetime.fromisoformat(str(b.checkIn).replace('Z', '+00:00'))
                    cout = b.checkOut if isinstance(b.checkOut, datetime) else datetime.fromisoformat(str(b.checkOut).replace('Z', '+00:00'))
                    diff = (cout - cin).days
                    if diff > 0:
                        nights = diff
                except Exception:
                    nights = 2
            b_rev = float(b.totalPrice or 0.0)
            if b_rev <= 0.0:
                b_rev = float(h.price) * nights
            h_revenue += b_rev
            h_nights += nights
            
        homes_breakdown.append({
            "homeId": str(h.id),
            "houseName": h.houseName,
            "location": h.location,
            "nightlyPrice": float(h.price),
            "photoUrl": getattr(h, "photo", None) or getattr(h, "photoUrl", None) or (h.photos[0] if getattr(h, "photos", None) else ""),
            "bookingsCount": len(h_bookings),
            "nightsBooked": h_nights,
            "grossRevenue": round(h_revenue, 0),
            "netEarnings": round(h_revenue * 0.97, 0)
        })
        
    flagship_rate = float(target_homes[0].price) if target_homes else 8000.0
    mohan_benchmark = {
        "scenarioName": "Mohan's 10-Guest 2-Night Model",
        "sampleGuests": 10,
        "sampleNights": 2,
        "sampleNightlyRate": flagship_rate,
        "projectedGross": round(10 * 2 * flagship_rate, 0),
        "projectedNet": round(10 * 2 * flagship_rate * 0.97, 0)
    }
    
    return {
        "success": True,
        "isDemoPortfolio": is_demo,
        "hostName": getattr(user, "firstName", None) or getattr(user, "email", "Mohan (Host)"),
        "currency": "INR",
        "currencySymbol": "₹",
        "summary": {
            "totalListings": len(target_homes),
            "totalBookings": len(confirmed_bookings),
            "totalNightsBooked": total_nights,
            "avgStayDuration": avg_stay,
            "totalGrossRevenue": round(total_gross, 0),
            "netPayout": net_payout,
            "platformFeePercent": platform_fee_percent,
            "avgBookingValue": avg_val
        },
        "homesBreakdown": homes_breakdown,
        "recentBookings": serialized_bookings[:10],
        "mohanBenchmark": mohan_benchmark
    }

