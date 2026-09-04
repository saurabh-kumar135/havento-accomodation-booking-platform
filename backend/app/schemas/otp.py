from pydantic import BaseModel, EmailStr

class SendOTPRequest(BaseModel):
    email: EmailStr
    firstName: str
    lastName: str
    password: str
    userType: str = "guest"

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class ResendOTPRequest(BaseModel):
    email: EmailStr

class PasswordResetRequest(BaseModel):
    email: EmailStr

class VerifyResetTokenRequest(BaseModel):
    token: str

class ResetPasswordSubmitRequest(BaseModel):
    token: str
    newPassword: str
