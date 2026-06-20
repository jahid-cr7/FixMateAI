"""Testable presentation helpers shared by the Streamlit Reports page."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any

from src.privacy import redact_sensitive_text


def selected_conversation_notes(messages: list[dict[str, Any]]) -> tuple[str, ...]:
    """Minimize and redact explicitly selected current-session conversation text."""
    notes: list[str] = []
    for message in messages[-20:]:
        role = str(message.get("role") or "message")
        content = message.get("content")
        if isinstance(content, str):
            notes.append(redact_sensitive_text(f"{role}: {content[:2000]}"))
        elif isinstance(content, dict) and content.get("direct_answer"):
            notes.append(
                redact_sensitive_text(
                    f"{role}: {str(content['direct_answer'])[:2000]}"
                )
            )
    return tuple(notes)


def utc_date_range(values: tuple[date, ...] | list[date]) -> tuple[datetime | None, datetime | None]:
    """Convert Streamlit date selections to an inclusive UTC range."""
    if len(values) != 2:
        return None, None
    return (
        datetime.combine(values[0], time.min, tzinfo=timezone.utc),
        datetime.combine(values[1], time.max, tzinfo=timezone.utc),
    )

