import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi import Response
from utils.security import get_password_hash
from utils.emailService import send_password_reset_email
from models.user import User
from models.passwordReset import PasswordReset
from schemas.otp import PasswordResetRequest, VerifyResetTokenRequest, ResetPasswordSubmitRequest

async def post_request_reset(req: PasswordResetRequest):
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

async def get_validate_reset_token(token: str):
    """Validate reset token via GET request matching React frontend validate/${token} call."""
    # 1. Check PasswordReset collection (Heaven_Python standard)
    record = await PasswordReset.find_one(PasswordReset.token == token)
    if record:
        now = datetime.now(timezone.utc)
        expiry = record.expiresAt if record.expiresAt.tzinfo else record.expiresAt.replace(tzinfo=timezone.utc)
        if now > expiry:
            await record.delete()
            return Response(
                status_code=400,
                content='{"success": false, "errors": ["Invalid or expired reset token"]}',
                media_type="application/json"
            )
        return {
            "success": True,
            "message": "Token is valid",
            "email": record.email
        }
        
    # 2. Check User collection with sha256 hash or plain token (Node.js HavenTo fallback)
    hashed_token = hashlib.sha256(token.encode()).hexdigest()
    user = await User.find_one(
        {"$or": [{"resetPasswordToken": hashed_token}, {"resetPasswordToken": token}]}
    )
    if user:
        reset_expires = getattr(user, "resetPasswordExpires", None)
        now_ms = datetime.now(timezone.utc).timestamp() * 1000
        if reset_expires:
            exp_ms = reset_expires.timestamp() * 1000 if isinstance(reset_expires, datetime) else float(reset_expires)
            if now_ms > exp_ms:
                return Response(
                    status_code=400,
                    content='{"success": false, "errors": ["Invalid or expired reset token"]}',
                    media_type="application/json"
                )
        return {
            "success": True,
            "message": "Token is valid",
            "email": user.email
        }
        
    return Response(
        status_code=400,
        content='{"success": false, "errors": ["Invalid or expired reset token"]}',
        media_type="application/json"
    )

async def post_verify_reset_token(req: VerifyResetTokenRequest):
    return await get_validate_reset_token(req.token)

async def post_reset_password(req: ResetPasswordSubmitRequest):
    # 1. Check PasswordReset collection
    record = await PasswordReset.find_one(PasswordReset.token == req.token)
    user = None
    if record:
        user = await User.find_one(User.email == record.email)
        await record.delete()
    else:
        # 2. Check User collection fallback
        hashed_token = hashlib.sha256(req.token.encode()).hexdigest()
        user = await User.find_one(
            {"$or": [{"resetPasswordToken": hashed_token}, {"resetPasswordToken": req.token}]}
        )

    if not user:
        return Response(
            status_code=400,
            content='{"success": false, "errors": ["Password reset link is invalid or expired."]}',
            media_type="application/json"
        )
        
    user.password = get_password_hash(req.newPassword)
    if hasattr(user, "resetPasswordToken"):
        user.resetPasswordToken = None
    if hasattr(user, "resetPasswordExpires"):
        user.resetPasswordExpires = None
    await user.save()
    
    return {
        "success": True,
        "message": "Password has been successfully updated! You can now log in."
    }
