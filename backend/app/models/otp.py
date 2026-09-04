from datetime import datetime, timezone, timedelta
from typing import Optional
from beanie import Document, Indexed
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

class PasswordReset(Document):
    email: EmailStr
    token: str
    expiresAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=1))
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "password_resets"
