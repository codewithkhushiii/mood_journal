"""
auth.py — Authentication Module
Handles password hashing, session cookies, and user auth middleware.
"""

import os
import bcrypt
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import Request, HTTPException
from dotenv import load_dotenv

load_dotenv()

# Secret key for signing session cookies
SECRET_KEY = os.getenv("SECRET_KEY", "moodboard-vibely-secret-key-change-in-prod-2024")
SESSION_MAX_AGE = 7 * 24 * 3600  # 7 days in seconds
COOKIE_NAME = "vibely_session"

serializer = URLSafeTimedSerializer(SECRET_KEY)


# ─── Password Hashing ────────────────────────────────────────
def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ─── Session Tokens ──────────────────────────────────────────
def create_session_token(user_id: str) -> str:
    """Create a signed session token containing the user ID."""
    return serializer.dumps({"uid": user_id})


def verify_session_token(token: str) -> dict | None:
    """Verify and decode a session token. Returns payload or None."""
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data
    except (BadSignature, SignatureExpired):
        return None


# ─── Request Helpers ─────────────────────────────────────────
def get_session_user_id(request: Request) -> str | None:
    """Extract user ID from session cookie. Returns None if not authenticated."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    data = verify_session_token(token)
    if not data or "uid" not in data:
        return None
    return data["uid"]


async def require_auth(request: Request) -> str:
    """Get authenticated user ID or raise 401. Use as a dependency."""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id
