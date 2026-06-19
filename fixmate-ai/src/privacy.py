"""Privacy helpers for screenshot analysis metadata and stored OCR text."""

from __future__ import annotations

import hashlib
import re

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(password|passwd|pwd|token|access[_ -]?token|api[_ -]?key|secret)"
    r"\s*[:=]\s*([^\s,;]+)",
    re.IGNORECASE,
)
BEARER_PATTERN = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]+=*", re.IGNORECASE)
WINDOWS_USER_PATH_PATTERN = re.compile(
    r"\b[A-Za-z]:\\Users\\[^\\\s]+(?:\\[^\s]*)?",
    re.IGNORECASE,
)
UNIX_USER_PATH_PATTERN = re.compile(r"(?<!\w)/(?:home|Users)/[^/\s]+(?:/[^\s]*)?")


def anonymize_image_filename(image_bytes: bytes, image_format: str) -> str:
    """Create a stable anonymous identifier without using the uploaded filename."""
    digest = hashlib.sha256(image_bytes).hexdigest()[:16]
    extension = ".png" if image_format.upper() == "PNG" else ".jpg"
    return f"image-{digest}{extension}"


def redact_sensitive_text(text: str) -> str:
    """Redact likely credentials, email addresses, and user-specific paths."""
    redacted = BEARER_PATTERN.sub("Bearer [REDACTED]", text)
    redacted = SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}=[REDACTED]",
        redacted,
    )
    redacted = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", redacted)
    redacted = WINDOWS_USER_PATH_PATTERN.sub("[REDACTED_PATH]", redacted)
    redacted = UNIX_USER_PATH_PATTERN.sub("[REDACTED_PATH]", redacted)
    return redacted

