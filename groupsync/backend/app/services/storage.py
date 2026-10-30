import uuid
from pathlib import Path
from typing import Protocol

from fastapi import HTTPException, status
from fastapi.responses import FileResponse, Response

from app.config import settings


class Storage(Protocol):
    """Swap in an S3 implementation later; routers only talk to this interface."""

    def save(self, group_id: int, data: bytes, ext: str) -> str: ...
    def delete(self, stored_path: str) -> None: ...
    def download_response(self, stored_path: str, filename: str, mime_type: str) -> Response: ...


class LocalStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    def save(self, group_id: int, data: bytes, ext: str) -> str:
        rel = Path(f"group_{group_id}") / f"{uuid.uuid4().hex}{ext}"
        target = self.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return rel.as_posix()

    def _resolve(self, stored_path: str) -> Path:
        path = (self.root / stored_path).resolve()
        if not path.is_relative_to(self.root):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
        return path

    def delete(self, stored_path: str) -> None:
        self._resolve(stored_path).unlink(missing_ok=True)

    def download_response(self, stored_path: str, filename: str, mime_type: str) -> Response:
        path = self._resolve(stored_path)
        if not path.is_file():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "File is missing from storage")
        return FileResponse(path, media_type=mime_type, filename=filename)


def get_storage() -> Storage:
    return LocalStorage(settings.upload_dir)
