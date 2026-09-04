from datetime import datetime, timezone, timedelta
from beanie import Document
from pydantic import Field, EmailStr

class PasswordReset(Document):
    email: EmailStr
    token: str
    expiresAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=1))
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "password_resets"
