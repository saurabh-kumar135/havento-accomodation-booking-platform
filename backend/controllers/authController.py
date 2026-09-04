import logging
from typing import Optional
from fastapi import HTTPException, status, Depends, Response
from beanie import PydanticObjectId
from utils.security import get_password_hash, verify_password, create_access_token
from models.user import User
from schemas.user import (
    RegisterRequest, 
    LoginRequest, 
    GoogleLoginRequest, 
    ChangePasswordRequest
)
from middleware.auth import get_current_user, get_current_user_optional

logger = logging.getLogger(__name__)

async def get_login():
    return {
        "success": True,
        "pageTitle": "Login",
        "currentPage": "login",
        "isLoggedIn": False
    }

async def get_signup():
    return {
        "success": True,
        "pageTitle": "Signup",
        "currentPage": "signup",
        "isLoggedIn": False
    }

async def check_session(user: Optional[User] = Depends(get_current_user_optional)):
    if user:
        return {
            "success": True,
            "isLoggedIn": True,
            "user": {
                "_id": str(user.id),
                "id": str(user.id),
                "firstName": user.firstName,
                "lastName": user.lastName,
                "email": user.email,
                "userType": user.userType,
                "avatar": user.avatar,
                "favourites": [str(fav) for fav in user.favourites]
            }
        }
    return {
        "success": True,
        "isLoggedIn": False,
        "user": None
    }

async def post_signup(req: RegisterRequest):
    existing_user = await User.find_one(User.email == req.email)
    if existing_user:
        return Response(
            status_code=422,
            content='{"success": false, "errors": ["Email already registered"]}',
            media_type="application/json"
        )
    
    hashed_pwd = get_password_hash(req.password)
    new_user = User(
        firstName=req.firstName,
        lastName=req.lastName,
        email=req.email,
        password=hashed_pwd,
        userType=req.userType,
        emailVerified=True
    )
    await new_user.insert()
    
    return {
        "success": True,
        "message": "User created successfully"
    }

async def post_login(req: LoginRequest, response: Response):
    user = await User.find_one(User.email == req.email)
    if not user:
        return Response(
            status_code=422,
            content='{"success": false, "errors": ["User does not exist"]}',
            media_type="application/json"
        )
        
    if not user.password or not verify_password(req.password, user.password):
        return Response(
            status_code=422,
            content='{"success": false, "errors": ["Invalid Password"]}',
            media_type="application/json"
        )
        
    token = create_access_token(subject=str(user.id))
    
    # Set HTTP-only session cookie
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
        "message": "Login successful",
        "token": token,
        "user": {
            "_id": str(user.id),
            "id": str(user.id),
            "firstName": user.firstName,
            "lastName": user.lastName,
            "email": user.email,
            "userType": user.userType,
            "avatar": user.avatar,
            "favourites": [str(fav) for fav in user.favourites]
        }
    }

async def post_google_login(req: GoogleLoginRequest, response: Response):
    user = await User.find_one(User.email == req.email)
    if not user:
        first_name = "User"
        last_name = ""
        if req.name:
            parts = req.name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""
            
        user = User(
            firstName=first_name,
            lastName=last_name,
            email=req.email,
            userType="guest",
            emailVerified=True,
            authProvider="google",
            avatar=req.picture
        )
        await user.insert()
        
    token = create_access_token(subject=str(user.id))
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
        "message": "Google login successful",
        "token": token,
        "user": {
            "_id": str(user.id),
            "id": str(user.id),
            "firstName": user.firstName,
            "lastName": user.lastName,
            "email": user.email,
            "userType": user.userType,
            "avatar": user.avatar,
            "favourites": [str(fav) for fav in user.favourites]
        }
    }

async def post_logout(response: Response):
    response.delete_cookie(key="token")
    return {
        "success": True,
        "message": "Logout successful"
    }

async def change_password(req: ChangePasswordRequest, user: User = Depends(get_current_user)):
    if not user.password or not verify_password(req.currentPassword, user.password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
        
    user.password = get_password_hash(req.newPassword)
    await user.save()
    return {
        "success": True,
        "message": "Password changed successfully"
    }
