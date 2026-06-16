"""
JWT token creation and verification.
"""

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import JWTError, jwt

from backend.config import JWT_ALGORITHM, JWT_EXPIRY_MINUTES

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")


def create_token(username: str, role: str) -> str:
    """Create a JWT token containing username and role."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES)
    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    """
    Verify and decode a JWT token.

    Returns:
        Dict with 'username' and 'role' on success, None on failure.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if username and role:
            return {"username": username, "role": role}
    except JWTError:
        pass
    return None
