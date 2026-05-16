import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Text, Table
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")
    shared_notes = relationship(
        "NoteShare",
        foreign_keys="NoteShare.shared_with_user_id",
        back_populates="shared_with_user",
        cascade="all, delete-orphan",
    )


class Note(Base):
    __tablename__ = "notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    pinned = Column(Boolean, default=False, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="notes")
    shares = relationship("NoteShare", back_populates="note", cascade="all, delete-orphan")


class NoteShare(Base):
    __tablename__ = "note_shares"

    note_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    shared_with_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    # Relationships
    note = relationship("Note", back_populates="shares")
    shared_with_user = relationship(
        "User",
        foreign_keys=[shared_with_user_id],
        back_populates="shared_notes",
    )
