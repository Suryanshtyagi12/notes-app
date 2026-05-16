import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import models
from database import get_db
from schemas import TokenData

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not set in the .env file")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return the bcrypt hash of a plain-text password."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the plain-text password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT utilities
# ---------------------------------------------------------------------------
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Encode a JWT with an expiry claim."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decode a JWT and return a TokenData object.
    Returns None if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            return None
        return TokenData(user_id=uuid.UUID(user_id_str))
    except (JWTError, ValueError):
        return None


# ---------------------------------------------------------------------------
# OAuth2 scheme — reads Bearer token from Authorization header
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    FastAPI dependency.
    Validates the Bearer token and returns the authenticated User ORM object.
    Raises HTTP 401 if the token is missing, invalid, or the user is not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = decode_access_token(token)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception

    return user
