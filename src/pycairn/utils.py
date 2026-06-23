from __future__ import annotations

from enum import StrEnum
import hashlib
from pathlib import Path
from datetime import datetime, timezone


def now() -> datetime:
    return datetime.now(timezone.utc)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


class Status(StrEnum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    skipped = "skipped"

SUCCESS_STATUSES = (Status.success, Status.skipped)