"""System scan API models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProcessMetric(BaseModel):
    """Privacy-safe process memory metric."""

    pid: int | None = None
    name: str
    memory_mb: float = Field(ge=0)


class SystemIssueSummary(BaseModel):
    """Issue attached to a system scan."""

    id: str
    code: str
    severity: str
    evidence: str
    explanation: str
    recommendation: str
    detected_at: datetime


class SystemScan(BaseModel):
    """One stored or newly collected system scan."""

    id: int
    collected_at: datetime
    os_name: str
    os_release: str
    architecture: str
    boot_time: datetime | None = None
    cpu_percent: float | None = None
    memory_percent: float | None = None
    disk_used_percent: float | None = None
    disk_free_percent: float | None = None
    health_score: int = Field(ge=0, le=100)
    top_processes: list[ProcessMetric]
    issues: list[SystemIssueSummary] = Field(default_factory=list)


class SystemHistoryItem(BaseModel):
    """Compact historical system record."""

    id: int
    collected_at: datetime
    cpu_percent: float | None = None
    memory_percent: float | None = None
    disk_used_percent: float | None = None
    disk_free_percent: float | None = None
    health_score: int
