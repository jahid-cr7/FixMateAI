"""Tests for issue-detection thresholds using simulated values."""

from src.detector import detect_issues


def test_no_issues_for_healthy_metrics() -> None:
    """Healthy simulated metrics should not create issues."""
    assert detect_issues(25.0, 50.0, 40.0) == []


def test_detects_all_threshold_violations() -> None:
    """Each rule should fire when its simulated value crosses the threshold."""
    issues = detect_issues(95.0, 90.0, 5.0)
    assert {issue["code"] for issue in issues} == {
        "CPU_HIGH",
        "MEMORY_HIGH",
        "DISK_LOW",
    }
    assert all(issue["explanation"] for issue in issues)
    assert all(issue["recommendation"] for issue in issues)


def test_exact_thresholds_do_not_trigger() -> None:
    """Rules use above/below comparisons, so exact boundaries are healthy."""
    assert detect_issues(90.0, 85.0, 10.0) == []


def test_unavailable_metrics_are_ignored() -> None:
    """Missing operating-system metrics should not crash or create false issues."""
    assert detect_issues(None, None, None) == []


def test_issue_severities() -> None:
    """High resource use and low disk space should have defined severities."""
    issues = detect_issues(91.0, 86.0, 9.0)
    severities = {issue["code"]: issue["severity"] for issue in issues}
    assert severities == {
        "CPU_HIGH": "high",
        "MEMORY_HIGH": "high",
        "DISK_LOW": "medium",
    }

