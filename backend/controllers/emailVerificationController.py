import random
import logging
from datetime import datetime, timezone, timedelta
from fastapi import Response
from utils.security import get_password_hash, create_access_token
from utils.emailService import send_otp_email
from models.user import User
from models.pendingVerification import PendingVerification
from schemas.otp import SendOTPRequest, VerifyOTPRequest, ResendOTPRequest

logger = logging.getLogger(__name__)

def generate_otp() -> str:
    return str(random.randint(100000, 999999))

async def post_send_otp(req: SendOTPRequest):
    existing = await User.find_one(User.email == req.email)
    if existing and existing.emailVerified:
        return Response(
            status_code=400,
            content='{"success": false, "errors": ["Email already registered"]}',
            media_type="application/json"
        )
        
    otp = generate_otp()
    hashed_pwd = get_password_hash(req.password)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    await PendingVerification.find(PendingVerification.email == req.email).delete()
    
    pending = PendingVerification(
        email=req.email,
        otp=otp,
        firstName=req.firstName,
        lastName=req.lastName,
        password=hashed_pwd,
        userType=req.userType,
        expiresAt=expires_at
    )
    await pending.insert()
    
    email_sent = await send_otp_email(req.email, otp, req.firstName)
    if not email_sent:
        await pending.delete()
        return Response(
            status_code=500,
            content='{"success": false, "errors": ["Failed to send verification email. Please try again."]}',
            media_type="application/json"
        )
        
    return {
        "success": True,
        "message": "Verification code sent to your email!"
    }

async def post_verify_otp(req: VerifyOTPRequest, response: Response):
    pending = await PendingVerification.find_one(PendingVerification.email == req.email)
    if not pending:
        return Response(
            status_code=400,
            content='{"success": false, "errors": ["Verification session expired. Please sign up again."]}',
            media_type="application/json"
        )
        
    now = datetime.now(timezone.utc)
    if pending.expiresAt.tzinfo is None:
        pending_expiry = pending.expiresAt.replace(tzinfo=timezone.utc)
    else:
        pending_expiry = pending.expiresAt
        
    if now > pending_expiry:
        await pending.delete()
        return Response(
            status_code=400,
            content='{"success": false, "errors": ["Verification code expired. Please request a new one."]}',
            media_type="application/json"
        )
        
    if pending.otp != req.otp:
        return Response(
            status_code=400,
            content='{"success": false, "errors": ["Invalid verification code"]}',
            media_type="application/json"
        )
        
    existing = await User.find_one(User.email == req.email)
    if existing and existing.emailVerified:
        await pending.delete()
        return Response(
            status_code=400,
            content='{"success": false, "errors": ["Email already verified. Please login."]}',
            media_type="application/json"
        )
        
    new_user = User(
        firstName=pending.firstName,
        lastName=pending.lastName,
        email=pending.email,
        password=pending.password,
        userType=pending.userType,
        emailVerified=True
    )
    await new_user.insert()
    await pending.delete()
    
    token = create_access_token(subject=str(new_user.id))
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * 30,
        samesite="lax",
        secure=False
    )
    
    return {
        "success": True,
        "message": "Email verified successfully!",
        "token": token,
        "user": {
            "_id": str(new_user.id),
            "id": str(new_user.id),
            "email": new_user.email,
            "firstName": new_user.firstName,
            "lastName": new_user.lastName,
            "userType": new_user.userType
        }
    }

async def post_resend_otp(req: ResendOTPRequest):
    pending = await PendingVerification.find_one(PendingVerification.email == req.email)
    if not pending:
        return Response(
            status_code=400,
            content='{"success": false, "errors": ["Verification session expired. Please sign up again."]}',
            media_type="application/json"
        )
        
    otp = generate_otp()
    pending.otp = otp
    pending.expiresAt = datetime.now(timezone.utc) + timedelta(minutes=10)
    await pending.save()
    
    email_sent = await send_otp_email(req.email, otp, pending.firstName)
    if not email_sent:
        return Response(
            status_code=500,
            content='{"success": false, "errors": ["Failed to send verification email. Please try again."]}',
            media_type="application/json"
        )
        
    return {
        "success": True,
        "message": "New verification code sent to your email!"
    }
