"""Tests for deterministic health-score deductions."""

from src.health_score import calculate_health_score


def test_healthy_system_scores_100() -> None:
    """A scan with no issues should receive the maximum score."""
    assert calculate_health_score([]) == 100


def test_score_deducts_by_severity() -> None:
    """Simulated severities should deduct their documented point values."""
    issues = [{"severity": "high"}, {"severity": "medium"}, {"severity": "low"}]
    assert calculate_health_score(issues) == 55


def test_score_never_drops_below_zero() -> None:
    """Many simulated issues should not produce a negative score."""
    assert calculate_health_score([{"severity": "high"}] * 10) == 0


def test_unknown_severity_has_no_deduction() -> None:
    """Unexpected severity labels should be handled safely."""
    assert calculate_health_score([{"severity": "unknown"}]) == 100

