"""
Demo user store.

In production this would be a database. For this project,
5 hardcoded users demonstrate role-based access control.
Passwords are SHA-256 hashed — production would use bcrypt.
"""

import hashlib


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


DEMO_USERS = {
    "dr.mehta": {
        "password_hash": _hash("doctor123"),
        "role": "doctor",
        "display_name": "Dr. Mehta",
    },
    "nurse.priya": {
        "password_hash": _hash("nurse123"),
        "role": "nurse",
        "display_name": "Nurse Priya",
    },
    "billing.karim": {
        "password_hash": _hash("billing123"),
        "role": "billing_executive",
        "display_name": "Billing Karim",
    },
    "tech.fatima": {
        "password_hash": _hash("tech123"),
        "role": "technician",
        "display_name": "Tech Fatima",
    },
    "admin.sys": {
        "password_hash": _hash("admin123"),
        "role": "admin",
        "display_name": "System Admin",
    },
}


def authenticate(username: str, password: str) -> dict | None:
    """
    Verify credentials. Returns user dict (without password_hash)
    on success, None on failure.
    """
    user = DEMO_USERS.get(username)
    if user and user["password_hash"] == _hash(password):
        return {
            "username": username,
            "role": user["role"],
            "display_name": user["display_name"],
        }
    return None
