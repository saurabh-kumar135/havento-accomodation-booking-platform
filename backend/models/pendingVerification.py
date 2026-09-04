from datetime import datetime, timezone, timedelta
from beanie import Document
from pydantic import Field, EmailStr

class PendingVerification(Document):
    email: EmailStr
    otp: str
    firstName: str
    lastName: str
    password: str
    userType: str = "guest"
    expiresAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=10))
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "pending_verifications"
