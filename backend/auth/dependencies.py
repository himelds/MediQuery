"""
FastAPI dependency for extracting authenticated user from JWT token.

Usage in routes:
    @router.post("/chat")
    def chat(user: dict = Depends(get_current_user)):
        role = user["role"]
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .jwt_handler import verify_token

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Extract and verify JWT from Authorization header.

    Raises 401 if token is missing, expired, or invalid.
    """
    token = credentials.credentials
    user = verify_token(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
