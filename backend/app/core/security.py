"""
Security utilities for authentication and authorization.
"""

import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, Union

import bcrypt
import jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The subject (usually user ID) to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    """
    Create a JWT refresh token.

    Args:
        subject: The subject (usually user ID) to encode in the token

    Returns:
        Encoded JWT refresh token string
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        The subject (user ID) if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        token_type_claim: str = payload.get("type")

        if user_id is None or token_type_claim != token_type:
            return None

        return user_id
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except jwt.PyJWTError:
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if a JWT token is expired.

    Args:
        token: The JWT token to check

    Returns:
        True if token is expired, False otherwise
    """
    try:
        jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return False
    except jwt.ExpiredSignatureError:
        return True
    except jwt.PyJWTError:
        return True


def get_token_payload(token: str) -> Optional[Dict[str, Any]]:
    """
    Get token payload without verification (for expired tokens).

    Args:
        token: The JWT token

    Returns:
        Token payload if valid format, None otherwise
    """
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        return None


def refresh_access_token(refresh_token: str) -> Optional[Tuple[str, str]]:
    """
    Generate new access token using refresh token.

    Args:
        refresh_token: Valid refresh token

    Returns:
        Tuple of (new_access_token, new_refresh_token) if successful, None otherwise
    """
    user_id = verify_token(refresh_token, "refresh")
    if not user_id:
        return None

    # Generate new tokens
    new_access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)

    return new_access_token, new_refresh_token


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: The plain text password
        hashed_password: The hashed password to verify against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: The plain text password to hash

    Returns:
        The hashed password
    """
    return pwd_context.hash(password)


def generate_password_reset_token() -> str:
    """
    Generate a secure random token for password reset.

    Returns:
        A secure random token string
    """
    return secrets.token_urlsafe(32)


def generate_email_verification_token() -> str:
    """
    Generate a secure random token for email verification.

    Returns:
        A secure random token string
    """
    return secrets.token_urlsafe(32)


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password strength according to security requirements.

    Args:
        password: The password to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    if len(password) > 128:
        errors.append("Password must be no more than 128 characters long")

    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")

    # Check for at least one special character
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        errors.append("Password must contain at least one special character")

    return len(errors) == 0, errors


def create_email_verification_token(email: str) -> str:
    """
    Create a JWT token for email verification.

    Args:
        email: The email address to verify

    Returns:
        Encoded JWT token for email verification
    """
    expire = datetime.utcnow() + timedelta(hours=24)  # 24 hour expiry
    to_encode = {"exp": expire, "email": email, "type": "email_verification"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_email_verification_token(token: str) -> Optional[str]:
    """
    Verify an email verification token.

    Args:
        token: The JWT token to verify

    Returns:
        The email address if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        token_type: str = payload.get("type")

        if email is None or token_type != "email_verification":
            return None

        return email
    except jwt.PyJWTError:
        return None


def create_password_reset_token(email: str) -> str:
    """
    Create a JWT token for password reset.

    Args:
        email: The email address for password reset

    Returns:
        Encoded JWT token for password reset
    """
    expire = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
    to_encode = {"exp": expire, "email": email, "type": "password_reset"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token.

    Args:
        token: The JWT token to verify

    Returns:
        The email address if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        token_type: str = payload.get("type")

        if email is None or token_type != "password_reset":
            return None

        return email
    except jwt.PyJWTError:
        return None


def generate_api_key() -> str:
    """
    Generate a secure API key.

    Returns:
        A secure random API key string
    """
    return f"kess_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage.

    Args:
        api_key: The API key to hash

    Returns:
        The hashed API key
    """
    return get_password_hash(api_key)


def verify_api_key(plain_api_key: str, hashed_api_key: str) -> bool:
    """
    Verify an API key against its hash.

    Args:
        plain_api_key: The plain text API key
        hashed_api_key: The hashed API key to verify against

    Returns:
        True if API key matches, False otherwise
    """
    return verify_password(plain_api_key, hashed_api_key)
