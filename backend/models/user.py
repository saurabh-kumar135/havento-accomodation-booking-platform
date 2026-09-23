from datetime import datetime, timezone
from typing import List, Optional
from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, EmailStr

class HostKyc(BaseModel):
    isVerified: bool = False
    documentType: Optional[str] = None
    documentNumber: Optional[str] = None
    maskedNumber: Optional[str] = None
    documentHash: Optional[str] = None
    fullNameAsOnDoc: Optional[str] = None
    status: str = "unverified"
    verificationRef: Optional[str] = None
    verifiedAt: Optional[datetime] = None

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
    hostKyc: Optional[HostKyc] = Field(default_factory=HostKyc)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
        use_state_management = True
