from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from .config import settings

password_hash = PasswordHash.recommended()  # Argon2

# Hash of a throwaway password, used to keep login timing uniform (explained below)
DUMMY_HASH = password_hash.hash("dummy-password")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)

def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),  # must be a string per the JWT spec
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)   

def decode_access_token(token: str) -> int | None:
    """Return the user id if the token is valid, otherwise None."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None