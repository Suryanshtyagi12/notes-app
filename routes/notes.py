import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
from auth import get_current_user
from database import get_db
from schemas import NoteCreate, NoteResponse, NoteUpdate, ShareNote

router = APIRouter(prefix="/notes", tags=["Notes"])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _has_access(note_id: uuid.UUID, user: models.User, db: Session) -> models.Note | None:
    """
    Return the Note if the user is the owner OR has a share record.
    Return None otherwise (caller should raise 404 — never leak existence).
    """
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if note is None:
        return None

    if note.owner_id == user.id:
        return note

    shared = (
        db.query(models.NoteShare)
        .filter(
            models.NoteShare.note_id == note_id,
            models.NoteShare.shared_with_user_id == user.id,
        )
        .first()
    )
    return note if shared else None


def _require_access(note_id: uuid.UUID, user: models.User, db: Session) -> models.Note:
    """Get note if user has read access, else raise 404 (no existence leak)."""
    note = _has_access(note_id, user, db)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


def _require_owner(note_id: uuid.UUID, user: models.User, db: Session) -> models.Note:
    """
    Get the note unconditionally, then assert ownership.
    - 404 if note doesn't exist (don't leak existence to non-owners).
    - 403 if note exists but user is not the owner (shared users get 403,
      not 404, because they already know the note exists via GET).
    """
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    if note.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this note",
        )
    return note


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    note_in: NoteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new note owned by the authenticated user."""
    note = models.Note(**note_in.model_dump(), owner_id=current_user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/", response_model=List[NoteResponse])
def list_notes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Return all notes the authenticated user owns OR has been shared with them.
    Pinned notes surface first; within each group, most-recently-updated first.
    """
    owned = db.query(models.Note).filter(models.Note.owner_id == current_user.id)

    shared_ids = (
        db.query(models.NoteShare.note_id)
        .filter(models.NoteShare.shared_with_user_id == current_user.id)
        .subquery()
    )
    shared = db.query(models.Note).filter(models.Note.id.in_(shared_ids))

    notes = (
        owned.union(shared)
        .order_by(models.Note.pinned.desc(), models.Note.updated_at.desc())
        .all()
    )
    return notes


@router.get("/{note_id}", response_model=NoteResponse)
def get_note(
    note_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Fetch a single note.
    Returns 404 for both non-existent notes AND notes the user has no access to
    — this prevents existence leakage.
    """
    return _require_access(note_id, current_user, db)


@router.put("/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: uuid.UUID,
    note_in: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Update title / content of a note.
    Only the owner may update. Shared users receive 403.
    """
    note = _require_owner(note_id, current_user, db)

    update_data = note_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(note, field, value)

    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Delete a note (owner only).
    Shared users who attempt deletion receive 403.
    """
    note = _require_owner(note_id, current_user, db)
    db.delete(note)
    db.commit()


@router.patch("/{note_id}/pin", response_model=NoteResponse)
def toggle_pin(
    note_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Toggle the pinned boolean on a note (owner only).
    Returns the updated note with the new pinned state.
    """
    note = _require_owner(note_id, current_user, db)
    note.pinned = not note.pinned
    db.commit()
    db.refresh(note)
    return note


@router.post("/{note_id}/share", status_code=status.HTTP_200_OK)
def share_note(
    note_id: uuid.UUID,
    share_in: ShareNote,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Share a note with another user by email.

    Validations (all owner-only):
    - 404 if the target email is not a registered user.
    - 400 if trying to share with yourself.
    - 400 if the note is already shared with that user.
    """
    note = _require_owner(note_id, current_user, db)

    target = (
        db.query(models.User)
        .filter(models.User.email == share_in.shared_with_email)
        .first()
    )
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user found with that email",
        )

    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot share a note with yourself",
        )

    already = (
        db.query(models.NoteShare)
        .filter(
            models.NoteShare.note_id == note_id,
            models.NoteShare.shared_with_user_id == target.id,
        )
        .first()
    )
    if already:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note is already shared with this user",
        )

    db.add(models.NoteShare(note_id=note_id, shared_with_user_id=target.id))
    db.commit()

    return {"message": "Note shared successfully"}


@router.delete("/{note_id}/share/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_share(
    note_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Revoke a previously granted share (owner only)."""
    _require_owner(note_id, current_user, db)

    share = (
        db.query(models.NoteShare)
        .filter(
            models.NoteShare.note_id == note_id,
            models.NoteShare.shared_with_user_id == user_id,
        )
        .first()
    )
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share record not found",
        )

    db.delete(share)
    db.commit()
