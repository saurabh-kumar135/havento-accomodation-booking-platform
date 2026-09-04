from typing import Optional
from fastapi import Request, HTTPException, status, Depends
from beanie import PydanticObjectId
from utils.security import decode_access_token
from models.user import User

async def get_current_user_optional(request: Request) -> Optional[User]:
    """Extract and validate user from Authorization header or cookie (optional)."""
    token = None
    
    # 1. Check Authorization Header: Bearer <token>
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
    # 2. Check cookies if header not present
    if not token:
        token = request.cookies.get("token") or request.cookies.get("jwt")
        
    if not token:
        return None
        
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
        
    user_id = payload["sub"]
    try:
        user = await User.get(PydanticObjectId(user_id))
        return user
    except Exception:
        return None

async def get_current_user(user: Optional[User] = Depends(get_current_user_optional)) -> User:
    """Dependency for protected endpoints requiring an authenticated user."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in."
        )
    return user

async def get_current_host(user: User = Depends(get_current_user)) -> User:
    """Dependency requiring the authenticated user to be a Host."""
    if user.userType != "host":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden. Host privileges required."
        )
    return user
