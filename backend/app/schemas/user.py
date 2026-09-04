from typing import List, Optional
from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    firstName: str
    lastName: str
    email: EmailStr
    password: str
    userType: str = "guest"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class GoogleLoginRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    picture: Optional[str] = None
    googleId: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str

class UpdateProfileRequest(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    avatar: Optional[str] = None
    experienceLevel: Optional[str] = None
    goals: Optional[str] = None
    onboarded: Optional[bool] = None
    role: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    firstName: str
    lastName: str
    email: str
    userType: str
    emailVerified: bool = False
    phoneVerified: bool = False
    authProvider: str = "local"
    authMethod: str = "email"
    avatar: Optional[str] = None
    favourites: List[str] = []
    experienceLevel: str = "intermediate"
    goals: str = ""
    onboarded: bool = False
    role: str = "other"

    model_config = {
        "from_attributes": True
    }
