import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select

from app.config import settings
from app.deps import CurrentUser, DbSession
from app.models import FileRecord
from app.schemas.workspace import FileOut
from app.services.access import authorize_group, require_member
from app.services.activity import log_activity
from app.services.storage import Storage, get_storage

router = APIRouter(tags=["files"])

# extension -> (mime type, magic-byte check)
ALLOWED: dict[str, tuple[str, callable]] = {
    ".pdf": ("application/pdf", lambda d: d.startswith(b"%PDF")),
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        lambda d: d.startswith(b"PK\x03\x04"),
    ),
    ".png": ("image/png", lambda d: d.startswith(b"\x89PNG\r\n\x1a\n")),
    ".jpg": ("image/jpeg", lambda d: d.startswith(b"\xff\xd8\xff")),
    ".jpeg": ("image/jpeg", lambda d: d.startswith(b"\xff\xd8\xff")),
    ".gif": ("image/gif", lambda d: d.startswith(b"GIF8")),
    ".webp": ("image/webp", lambda d: d[:4] == b"RIFF" and d[8:12] == b"WEBP"),
}


def sanitize_filename(raw: str | None) -> str:
    name = Path((raw or "").replace("\\", "/")).name
    name = re.sub(r"[^\w.\- ]", "_", name).strip(" .")
    stem, dot, ext = name.rpartition(".")
    if not dot or not stem:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid file name")
    return f"{stem[:100]}.{ext.lower()}"


@router.post("/groups/{group_id}/files", response_model=FileOut, status_code=status.HTTP_201_CREATED)
def upload_file(
    group_id: int,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    storage: Storage = Depends(get_storage),
):
    require_member(db, group_id, user)
    filename = sanitize_filename(file.filename)
    ext = Path(filename).suffix
    if ext not in ALLOWED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF, DOCX and image files (PNG, JPG, GIF, WebP) are allowed")

    limit = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)  # read one byte past the limit to detect oversize without buffering more
    if len(data) > limit:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"File exceeds {settings.max_upload_mb} MB")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is empty")
    mime, magic_ok = ALLOWED[ext]
    if not magic_ok(data):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File content does not match its extension")

    # Same name in the same group = new version; old versions are kept
    latest = db.scalar(
        select(func.max(FileRecord.version)).where(FileRecord.group_id == group_id, FileRecord.filename == filename)
    )
    version = (latest or 0) + 1
    stored_path = storage.save(group_id, data, ext)
    record = FileRecord(
        group_id=group_id, uploader_id=user.id, filename=filename, stored_path=stored_path,
        version=version, size=len(data), mime_type=mime,
    )
    db.add(record)
    db.flush()
    log_activity(db, group_id, user.id, "file_uploaded", f"{user.name} uploaded {filename} (v{version})", record.id)
    try:
        db.commit()
    except Exception:
        storage.delete(stored_path)
        raise
    out = FileOut.model_validate(record)
    return out


@router.get("/groups/{group_id}/files", response_model=list[FileOut])
def list_files(group_id: int, user: CurrentUser, db: DbSession):
    authorize_group(db, group_id, user)
    records = list(
        db.scalars(select(FileRecord).where(FileRecord.group_id == group_id).order_by(FileRecord.uploaded_at.desc(), FileRecord.id.desc()))
    )
    newest: dict[str, int] = {}
    for r in records:
        newest[r.filename] = max(newest.get(r.filename, 0), r.version)
    return [FileOut.model_validate(r).model_copy(update={"is_latest": r.version == newest[r.filename]}) for r in records]


@router.get("/files/{file_id}/download")
def download_file(
    file_id: int, user: CurrentUser, db: DbSession, storage: Storage = Depends(get_storage)
):
    record = db.get(FileRecord, file_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    authorize_group(db, record.group_id, user)
    return storage.download_response(record.stored_path, record.filename, record.mime_type)
