"""Security utilities for API key authentication and hashing."""

from typing import cast

from passlib.context import CryptContext

# Password hashing context (for future user authentication)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return cast(bool, pwd_context.verify(plain_password, hashed_password))


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return cast(str, pwd_context.hash(password))


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    # Simple hash for API keys (in production, use proper secret hashing)
    import hashlib
    return hashlib.sha256(api_key.encode()).hexdigest()
