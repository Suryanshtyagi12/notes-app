from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_serializer


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    """JSON body for POST /auth/login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime) -> str:
        """Always return created_at as an ISO 8601 string."""
        return dt.isoformat()


# ---------------------------------------------------------------------------
# Token schemas
# ---------------------------------------------------------------------------

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[uuid.UUID] = None


# ---------------------------------------------------------------------------
# Note schemas
# ---------------------------------------------------------------------------

class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: Optional[str] = None
    pinned: bool = False


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = None
    pinned: Optional[bool] = None


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content: Optional[str]
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    pinned: bool

    @field_serializer("created_at", "updated_at")
    def serialize_dt(self, dt: datetime) -> str:
        """Always return datetimes as ISO 8601 strings."""
        return dt.isoformat()


# ---------------------------------------------------------------------------
# Share schemas
# ---------------------------------------------------------------------------

class ShareNote(BaseModel):
    """Body for sharing a note with another user."""
    shared_with_email: EmailStr
