import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Response, HTTPException
from app.core.security import get_password_hash
from app.core.email import send_password_reset_email
from app.models.user import User
from app.models.otp import PasswordReset
from app.schemas.otp import PasswordResetRequest, VerifyResetTokenRequest, ResetPasswordSubmitRequest

router = APIRouter(prefix="/password-reset", tags=["Password Reset"])

@router.post("/request")
async def request_password_reset(req: PasswordResetRequest):
    user = await User.find_one(User.email == req.email)
    if not user:
        return Response(
            status_code=404,
            content='{"success": false, "errors": ["No account with that email address exists."]}',
            media_type="application/json"
        )
        
    token = secrets.token_hex(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    await PasswordReset.find(PasswordReset.email == req.email).delete()
    reset_record = PasswordReset(
        email=req.email,
        token=token,
        expiresAt=expires_at
    )
    await reset_record.insert()
    
    await send_password_reset_email(req.email, token, user.firstName)
    
    return {
        "success": True,
        "message": "Password reset link sent to your email!"
    }

@router.post("/verify-token")
async def verify_reset_token(req: VerifyResetTokenRequest):
    record = await PasswordReset.find_one(PasswordReset.token == req.token)
    if not record:
        return Response(
            status_code=400,
            content='{"success": false, "errors": ["Password reset link is invalid."]}',
            media_type="application/json"
        )
        
    now = datetime.now(timezone.utc)
    expiry = record.expiresAt if record.expiresAt.tzinfo else record.expiresAt.replace(tzinfo=timezone.utc)
    if now > expiry:
        await record.delete()
        return Response(
            status_code=400,
            content='{"success": false, "errors": ["Password reset link has expired."]}',
            media_type="application/json"
        )
        
    return {
        "success": True,
        "email": record.email
    }

@router.post("/reset")
async def reset_password(req: ResetPasswordSubmitRequest):
    record = await PasswordReset.find_one(PasswordReset.token == req.token)
    if not record:
        return Response(
            status_code=400,
            content='{"success": false, "errors": ["Password reset link is invalid or expired."]}',
            media_type="application/json"
        )
        
    user = await User.find_one(User.email == record.email)
    if not user:
        return Response(
            status_code=404,
            content='{"success": false, "errors": ["User not found."]}',
            media_type="application/json"
        )
        
    user.password = get_password_hash(req.newPassword)
    await user.save()
    await record.delete()
    
    return {
        "success": True,
        "message": "Password has been successfully updated! You can now log in."
    }
