from fastapi import APIRouter, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import Note, User
from app.schemas.workspace import NoteCreate, NoteOut
from app.services.access import authorize_group, require_member
from app.services.activity import log_activity

router = APIRouter(tags=["notes"])


def _out(note: Note, author_name: str) -> NoteOut:
    return NoteOut(
        id=note.id, group_id=note.group_id, author_id=note.author_id,
        author_name=author_name, content=note.content, created_at=note.created_at,
    )


@router.post("/groups/{group_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(group_id: int, body: NoteCreate, user: CurrentUser, db: DbSession):
    require_member(db, group_id, user)
    note = Note(group_id=group_id, author_id=user.id, content=body.content.strip())
    db.add(note)
    db.flush()
    log_activity(db, group_id, user.id, "note_added", f"{user.name} added a note", note.id)
    db.commit()
    return _out(note, user.name)


@router.get("/groups/{group_id}/notes", response_model=list[NoteOut])
def list_notes(group_id: int, user: CurrentUser, db: DbSession):
    authorize_group(db, group_id, user)
    rows = db.execute(
        select(Note, User.name).join(User, User.id == Note.author_id)
        .where(Note.group_id == group_id).order_by(Note.created_at.desc(), Note.id.desc())
    ).all()
    return [_out(n, name) for n, name in rows]
