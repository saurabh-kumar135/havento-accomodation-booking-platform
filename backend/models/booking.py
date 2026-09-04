from datetime import datetime, timezone
from beanie import Document, PydanticObjectId
from pydantic import Field

class Booking(Document):
    homeId: PydanticObjectId
    userId: PydanticObjectId
    checkIn: str
    checkOut: str
    totalPrice: float
    guests: int = 1
    status: str = "confirmed"  # "confirmed", "cancelled", "completed"
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "bookings"
        use_state_management = True
