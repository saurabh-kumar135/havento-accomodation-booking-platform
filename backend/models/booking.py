from datetime import datetime, timezone
from beanie import Document, PydanticObjectId
from pydantic import Field

from typing import Optional, Any

class Booking(Document):
    homeId: Optional[PydanticObjectId] = None
    home: Optional[PydanticObjectId] = None
    userId: Optional[PydanticObjectId] = None
    user: Optional[PydanticObjectId] = None
    checkIn: Optional[Any] = None
    checkOut: Optional[Any] = None
    totalPrice: Optional[float] = 0.0
    guests: int = 1
    status: str = "confirmed"  # "confirmed", "cancelled", "completed"
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "bookings"
        use_state_management = True
