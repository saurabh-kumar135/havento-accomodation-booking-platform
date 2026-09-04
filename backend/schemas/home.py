from typing import List, Optional
from pydantic import BaseModel

class HomeCreate(BaseModel):
    houseName: str
    price: float
    location: str
    rating: Optional[float] = 4.5
    photo: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = "Trending"
    amenities: Optional[List[str]] = []

class HomeUpdate(BaseModel):
    houseName: Optional[str] = None
    price: Optional[float] = None
    location: Optional[str] = None
    rating: Optional[float] = None
    photo: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    amenities: Optional[List[str]] = None

class HomeResponse(BaseModel):
    id: str
    _id: Optional[str] = None
    houseName: str
    price: float
    location: str
    rating: float
    photo: Optional[str] = None
    description: Optional[str] = None
    category: str
    host: Optional[str] = None
    amenities: List[str] = []

    model_config = {
        "from_attributes": True
    }
