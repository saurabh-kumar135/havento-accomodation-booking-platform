from typing import Optional
from pydantic import BaseModel

class BookingCreate(BaseModel):
    homeId: str
    checkIn: str
    checkOut: str
    totalPrice: float
    guests: Optional[int] = 1

class BookingResponse(BaseModel):
    id: str
    _id: Optional[str] = None
    homeId: str
    userId: str
    checkIn: str
    checkOut: str
    totalPrice: float
    guests: int
    status: str
    home: Optional[dict] = None

    model_config = {
        "from_attributes": True
    }
