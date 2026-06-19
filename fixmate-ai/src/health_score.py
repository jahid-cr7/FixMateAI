"""Overall health-score calculation."""

from collections.abc import Iterable, Mapping

SEVERITY_DEDUCTIONS = {"high": 25, "medium": 15, "low": 5}


def calculate_health_score(issues: Iterable[Mapping[str, object]]) -> int:
    """Calculate a 0-100 score by deducting points for each detected issue."""
    deduction = sum(
        SEVERITY_DEDUCTIONS.get(str(issue.get("severity", "")).lower(), 0)
        for issue in issues
    )
    return max(0, 100 - deduction)

