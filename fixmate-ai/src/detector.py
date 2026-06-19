"""Pure rules for detecting common system-health issues."""

from __future__ import annotations

from typing import TypedDict

from src.recommendations import (
    CPU_HIGH_EXPLANATION,
    CPU_HIGH_RECOMMENDATION,
    DISK_LOW_EXPLANATION,
    DISK_LOW_RECOMMENDATION,
    MEMORY_HIGH_EXPLANATION,
    MEMORY_HIGH_RECOMMENDATION,
)


class Issue(TypedDict):
    """A system-health issue produced by a detection rule."""

    code: str
    severity: str
    metric: str
    value: float
    explanation: str
    recommendation: str


def detect_issues(
    cpu_percent: float | None,
    memory_percent: float | None,
    disk_free_percent: float | None,
) -> list[Issue]:
    """Return issues for available metrics that cross the MVP thresholds."""
    issues: list[Issue] = []

    if cpu_percent is not None and cpu_percent > 90:
        issues.append(
            {
                "code": "CPU_HIGH",
                "severity": "high",
                "metric": "CPU usage",
                "value": cpu_percent,
                "explanation": CPU_HIGH_EXPLANATION,
                "recommendation": CPU_HIGH_RECOMMENDATION,
            }
        )

    if memory_percent is not None and memory_percent > 85:
        issues.append(
            {
                "code": "MEMORY_HIGH",
                "severity": "high",
                "metric": "Memory usage",
                "value": memory_percent,
                "explanation": MEMORY_HIGH_EXPLANATION,
                "recommendation": MEMORY_HIGH_RECOMMENDATION,
            }
        )

    if disk_free_percent is not None and disk_free_percent < 10:
        issues.append(
            {
                "code": "DISK_LOW",
                "severity": "medium",
                "metric": "Disk free space",
                "value": disk_free_percent,
                "explanation": DISK_LOW_EXPLANATION,
                "recommendation": DISK_LOW_RECOMMENDATION,
            }
        )

    return issues

