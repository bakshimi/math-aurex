"""Password hashing, JWT issuance/verification, and a lightweight login rate limiter."""
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import bcrypt
import jwt

from app.config import settings

# --- Passwords ---------------------------------------------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# --- JWT -----------------------------------------------------------------

def create_access_token(user_id: int, username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None


# --- Basic login rate limiting (per username, in-memory) -----------------

_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 60
_failed_attempts: Dict[str, list] = {}


def is_rate_limited(key: str) -> bool:
    now = time.time()
    attempts = [t for t in _failed_attempts.get(key, []) if now - t < _WINDOW_SECONDS]
    _failed_attempts[key] = attempts
    return len(attempts) >= _MAX_ATTEMPTS


def record_failed_attempt(key: str) -> None:
    _failed_attempts.setdefault(key, []).append(time.time())


def clear_failed_attempts(key: str) -> None:
    _failed_attempts.pop(key, None)
