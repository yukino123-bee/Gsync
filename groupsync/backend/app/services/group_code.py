import re
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Group

# No 0/O, 1/I or L, so a code read aloud or off a screen can't be mistyped
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
PREFIX = "GS-"
CODE_LENGTH = 6
_VALID = re.compile(rf"^GS-[{ALPHABET}]{{{CODE_LENGTH}}}$")


def normalize_code(raw: str) -> str:
    """Forgiving input: trims, uppercases, and accepts 'gs 4k7p2q' or just '4K7P2Q'."""
    cleaned = re.sub(r"[\s_]+", "", raw.strip().upper())
    if cleaned.startswith("GS") and not cleaned.startswith(PREFIX):
        cleaned = "GS-" + cleaned[2:]
    if not cleaned.startswith(PREFIX):
        cleaned = PREFIX + cleaned
    return cleaned


def is_valid_format(code: str) -> bool:
    return bool(_VALID.match(code))


def generate_code(db: Session) -> str:
    """A fresh code that no group uses yet (collisions are astronomically rare, but checked)."""
    while True:
        code = PREFIX + "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        if db.scalar(select(Group.id).where(Group.group_code == code)) is None:
            return code
