"""Unified system/network issue models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class SeverityFilter(str, Enum):
    """Supported severity filter values."""

    high = "high"
    medium = "medium"
    low = "low"


class IssueTypeFilter(str, Enum):
    """Supported issue source filters."""

    system = "system"
    network = "network"


class IssueRecord(BaseModel):
    """Privacy-redacted issue from either diagnostic source."""

    id: str
    issue_type: str
    code: str
    severity: str
    evidence: str
    explanation: str
    recommendation: str
    detected_at: datetime

