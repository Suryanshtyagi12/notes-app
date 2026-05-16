from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
from auth import create_access_token, get_current_user, hash_password, verify_password
from database import get_db
from schemas import LoginRequest, Token, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    - Validates email format (handled by Pydantic EmailStr).
    - Returns 400 if the email is already taken.
    - Returns 201 {"message": "User registered successfully"} on success.
    """
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Email already exists"},
        )

    new_user = models.User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
    )
    db.add(new_user)
    db.commit()
    return {"message": "User registered successfully"}


@router.post("/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate with email + password (JSON body).

    - Returns JWT access_token with 24-hour expiry on success.
    - Returns 401 {"message": "Invalid email or password"} on failure.
    """
    _invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"message": "Invalid email or password"},
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise _invalid

    token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user
