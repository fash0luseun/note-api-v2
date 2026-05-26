"""
auth.py — Authentication Module
=================================
Handles:
- Password hashing (bcrypt)
- JWT token creation and verification
- Auth middleware (dependency injection for protected routes)
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

# ──────────────────────────────────────────────
# 1. CONFIGURATION
# ──────────────────────────────────────────────

# Secret key for signing JWTs — in production, use a long random string
# stored in an environment variable, NEVER hardcoded
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")

ALGORITHM = "HS256"  # HMAC with SHA-256 — standard for JWT signing
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token expires after 30 minutes


# ──────────────────────────────────────────────
# 2. PASSWORD HASHING (bcrypt)
# ──────────────────────────────────────────────

# CryptContext handles hashing and verification
# bcrypt is intentionally slow (~100ms per hash) to prevent brute-force attacks
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """
    Hash a plain text password using bcrypt.
    
    Example:
        "mypassword123" → "$2b$12$LJ3m4ys8Rk.XzVGHwN3Oe..."
    
    The result includes the salt (random data) and the hash together,
    so you don't need to store the salt separately.
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check if a plain text password matches a stored hash.
    
    This re-hashes the plain password with the same salt and compares.
    Returns True if they match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


# ──────────────────────────────────────────────
# 3. JWT TOKEN CREATION
# ──────────────────────────────────────────────

def create_access_token(user_id: int, username: str) -> str:
    """
    Create a signed JWT token containing the user's identity.
    
    The token payload contains:
        - sub (subject): the user's ID
        - username: for display purposes
        - exp (expiration): when the token becomes invalid
    
    The token is SIGNED with our secret key, so if anyone
    tampers with the payload, the signature check will fail.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),      # subject — WHO this token represents
        "username": username,      # convenience field
        "exp": expire,             # expiration time
    }

    # jwt.encode signs the payload with our secret key
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


# ──────────────────────────────────────────────
# 4. JWT TOKEN VERIFICATION
# ──────────────────────────────────────────────

def verify_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token.
    
    Returns the payload dict if valid, None if invalid/expired.
    
    This checks:
    1. The signature matches (token wasn't tampered with)
    2. The token hasn't expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return payload
    except JWTError:
        return None


# ──────────────────────────────────────────────
# 5. AUTH MIDDLEWARE (FastAPI Dependency)
# ──────────────────────────────────────────────

# HTTPBearer extracts the token from the "Authorization: Bearer <token>" header
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    FastAPI dependency that protects endpoints.
    
    How it works:
    1. Extracts the Bearer token from the Authorization header
    2. Verifies and decodes the JWT
    3. Returns the user info if valid
    4. Raises 401 Unauthorized if invalid
    
    Usage in endpoints:
        @app.get("/notes")
        def get_notes(user: dict = Depends(get_current_user)):
            # 'user' is guaranteed to be authenticated here
            user_id = user["sub"]
    """
    token = credentials.credentials

    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload
