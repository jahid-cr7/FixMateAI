"""Bounded privacy-safe JSON queue for temporarily unavailable agent uploads."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fixmate_agent.config import clean_queue_dir
from src.privacy import redact_sensitive_text

ALLOWED_ENDPOINTS = {
    "/api/v1/agent/register",
    "/api/v1/agent/heartbeat",
    "/api/v1/agent/scans",
}
SENSITIVE_KEYS = {"token", "password", "secret", "authorization", "api_key"}
MAX_QUEUE_FILE_BYTES = 256 * 1024


class QueueError(RuntimeError):
    """Safe queue error without payload or path disclosure."""


@dataclass(frozen=True)
class QueueStatus:
    """Summary safe for CLI display."""

    queued: int
    corrupted: int
    total_bytes: int


def _sanitize(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _sanitize(item)
            for key, item in value.items()
            if str(key).casefold() not in SENSITIVE_KEYS
        }
    return value


class UploadQueue:
    """Persist allowlisted redacted requests without authentication headers."""

    def __init__(self, directory: Path, max_files: int = 100) -> None:
        self.directory = clean_queue_dir(directory)
        self.max_files = max(1, min(max_files, 10_000))

    def _files(self) -> list[Path]:
        if not self.directory.exists():
            return []
        return sorted(
            path
            for path in self.directory.glob("queue-*.json")
            if path.parent.resolve(strict=False) == self.directory
        )

    def enqueue(self, endpoint: str, payload: dict[str, Any]) -> Path:
        """Atomically append one sanitized upload while enforcing a file cap."""
        if endpoint not in ALLOWED_ENDPOINTS:
            raise QueueError("The upload endpoint is not allowed.")
        if len(self._files()) >= self.max_files:
            raise QueueError("The offline queue has reached its configured limit.")
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise QueueError("The offline queue could not be prepared.") from error
        try:
            self.directory.chmod(0o700)
        except OSError:
            pass
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        identifier = uuid.uuid4().hex
        destination = self.directory / f"queue-{stamp}-{identifier}.json"
        temporary = self.directory / f".queue-{identifier}.tmp"
        envelope = {
            "version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "endpoint": endpoint,
            "payload": _sanitize(payload),
        }
        encoded = json.dumps(envelope, sort_keys=True).encode("utf-8")
        if len(encoded) > MAX_QUEUE_FILE_BYTES:
            raise QueueError("The upload payload exceeds the queue file limit.")
        try:
            with temporary.open("xb") as handle:
                handle.write(encoded)
            try:
                temporary.chmod(0o600)
            except OSError:
                pass
            os.replace(temporary, destination)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise QueueError("The offline queue could not be written.") from error
        return destination

    def read(self, path: Path) -> tuple[str, dict[str, Any]]:
        """Validate and read one internally named queue entry."""
        if (
            path.parent.resolve(strict=False) != self.directory
            or path.is_symlink()
            or not path.name.startswith("queue-")
            or path.suffix != ".json"
        ):
            raise QueueError("The queue entry path is unsafe.")
        try:
            if path.stat().st_size > MAX_QUEUE_FILE_BYTES:
                raise QueueError("The queue entry exceeds the file limit.")
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise QueueError("The queue entry is corrupted.") from error
        endpoint = value.get("endpoint") if isinstance(value, dict) else None
        payload = value.get("payload") if isinstance(value, dict) else None
        if endpoint not in ALLOWED_ENDPOINTS or not isinstance(payload, dict):
            raise QueueError("The queue entry is corrupted.")
        return endpoint, _sanitize(payload)

    def status(self) -> QueueStatus:
        """Count valid and malformed entries without exposing their contents."""
        queued = corrupted = total_bytes = 0
        for path in self._files():
            try:
                total_bytes += path.stat().st_size
                self.read(path)
                queued += 1
            except (OSError, QueueError):
                corrupted += 1
        return QueueStatus(queued=queued, corrupted=corrupted, total_bytes=total_bytes)

    def entries(self) -> list[Path]:
        """Return oldest-first internally generated queue paths."""
        return self._files()

    def delete(self, path: Path) -> None:
        """Delete only a validated entry after confirmed upload success."""
        if (
            path.parent.resolve(strict=False) != self.directory
            or path.is_symlink()
            or not path.name.startswith("queue-")
            or path.suffix != ".json"
        ):
            raise QueueError("The queue entry path is unsafe.")
        path.unlink(missing_ok=True)
