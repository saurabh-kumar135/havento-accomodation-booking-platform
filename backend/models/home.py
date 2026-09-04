from datetime import datetime, timezone
from typing import List, Optional
from beanie import Document, PydanticObjectId
from pydantic import Field

class Home(Document):
    houseName: str
    price: float
    location: str
    rating: float = 4.5
    photo: Optional[str] = None
    photos: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    category: str = "Trending"
    host: Optional[PydanticObjectId] = None
    amenities: List[str] = Field(default_factory=list)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "homes"
        use_state_management = True
