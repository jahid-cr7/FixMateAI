"""Tests for anonymization and sensitive OCR-text redaction."""

from src.privacy import anonymize_image_filename, redact_sensitive_text


def test_anonymized_filename_ignores_original_name() -> None:
    """Stored identifiers should be content hashes with trusted extensions."""
    name = anonymize_image_filename(b"generated image bytes", "PNG")
    assert name.startswith("image-")
    assert name.endswith(".png")
    assert "/" not in name and "\\" not in name


def test_redacts_likely_sensitive_text() -> None:
    """Passwords, tokens, email, and user paths must not reach SQLite verbatim."""
    source = (
        "email alice@example.com password=hunter2 token:abc123 "
        "Bearer eyJ.secret.value C:\\Users\\Alice\\private\\error.log "
        "/home/bob/projects/private.txt"
    )
    redacted = redact_sensitive_text(source)
    assert "alice@example.com" not in redacted
    assert "hunter2" not in redacted
    assert "abc123" not in redacted
    assert "eyJ.secret.value" not in redacted
    assert "Alice" not in redacted
    assert "/home/bob" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PATH]" in redacted

