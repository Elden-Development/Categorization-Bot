"""
Authentication utilities for Categorization-Bot
Handles password hashing, JWT tokens, and user authentication
"""

from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
import models
import os
import secrets
from dotenv import load_dotenv

load_dotenv()

# Environment detection
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT in ("production", "prod")

# Insecure default keys that should never be used in production
INSECURE_DEFAULTS = {
    "your-secret-key-change-this-in-production",
    "change-this-in-production",
    "secret",
    "secret-key",
    "your-secret-key",
    "changeme",
    "changethis",
}


def _get_secret_key() -> str:
    """
    Get and validate the SECRET_KEY for JWT signing.

    In production: Fails loudly if SECRET_KEY is not set or is insecure.
    In development: Uses a generated key with a warning if not configured.
    """
    secret_key = os.getenv("SECRET_KEY", "").strip()

    # Check if secret key is missing or insecure
    is_missing = not secret_key
    is_insecure = secret_key.lower() in INSECURE_DEFAULTS or len(secret_key) < 32

    if IS_PRODUCTION:
        if is_missing:
            raise RuntimeError(
                "FATAL: SECRET_KEY environment variable is not set. "
                "This is required in production. Generate one with: "
                "python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        if is_insecure:
            raise RuntimeError(
                "FATAL: SECRET_KEY is insecure (too short or using a default value). "
                "Generate a secure key with: "
                "python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
    else:
        # Development mode
        if is_missing or is_insecure:
            # Generate a temporary key for development
            generated_key = secrets.token_urlsafe(64)
            print("\n" + "=" * 70)
            print("⚠️  WARNING: SECRET_KEY not configured or insecure!")
            print("   Using a temporary generated key for this session.")
            print("   Sessions will NOT persist across restarts.")
            print("\n   To fix, add to your .env file:")
            print(f'   SECRET_KEY="{secrets.token_urlsafe(64)}"')
            print("=" * 70 + "\n")
            return generated_key

    return secret_key


# JWT settings
SECRET_KEY = _get_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# OAuth2 scheme for required authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# OAuth2 scheme for optional authentication (doesn't auto-error on missing token)
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token

    Args:
        data: Dictionary containing user data to encode
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Get current authenticated user from JWT token

    Args:
        token: JWT token from request
        db: Database session

    Returns:
        Current user object

    Raises:
        HTTPException: If user is not found or inactive
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token)
    username: str = payload.get("sub")

    if username is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == username).first()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    """
    Get current user if authenticated, otherwise return None

    This is useful for endpoints that work both with and without authentication

    Args:
        token: Optional JWT token from request
        db: Database session

    Returns:
        Current user object or None
    """
    if not token:
        return None

    try:
        return get_current_user(token, db)
    except HTTPException:
        return None


def authenticate_user(username: str, password: str, db: Session) -> Optional[models.User]:
    """
    Authenticate a user with username and password

    Args:
        username: Username
        password: Plain text password
        db: Database session

    Returns:
        User object if authentication successful, None otherwise
    """
    user = db.query(models.User).filter(models.User.username == username).first()

    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def get_admin_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Verify current user is an admin

    Args:
        current_user: Current authenticated user

    Returns:
        User object if user is admin

    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user
