"""Screenshot-analysis metadata models with no OCR or image content."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ScreenshotAnalysisRecord(BaseModel):
    """Safe metadata for a previous screenshot analysis."""

    id: int
    analyzed_at: datetime
    matched_issue_id: str | None = None
    confidence_score: float | None = None

