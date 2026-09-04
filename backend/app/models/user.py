from datetime import datetime, timezone
from typing import List, Optional
from beanie import Document, Indexed, Link, PydanticObjectId
from pydantic import Field, EmailStr

class User(Document):
    firstName: str
    lastName: str
    email: EmailStr
    password: Optional[str] = None
    userType: str = "guest"  # "guest" or "host"
    favourites: List[PydanticObjectId] = Field(default_factory=list)
    emailVerified: bool = False
    phoneVerified: bool = False
    authProvider: str = "local"  # "local" or "google"
    authMethod: str = "email"
    avatar: Optional[str] = None
    experienceLevel: str = "intermediate"
    goals: str = ""
    onboarded: bool = False
    role: str = "other"
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
        use_state_management = True
