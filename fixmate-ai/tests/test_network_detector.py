"""Tests for pure network issue-detection rules."""

from src.network_detector import detect_network_issues


def _diagnostic(**overrides: object) -> dict[str, object]:
    """Create a connected simulated diagnostic with optional overrides."""
    result: dict[str, object] = {
        "target_host": "1.1.1.1",
        "target_port": 443,
        "timeout_seconds": 1.0,
        "latency_threshold_ms": 150.0,
        "active_interfaces": ["Ethernet"],
        "internet_connected": True,
        "timed_out": False,
        "latency_ms": 20.0,
    }
    result.update(overrides)
    return result


def test_connected_condition_has_no_issues() -> None:
    """A healthy simulated connection should produce no issues."""
    assert detect_network_issues(_diagnostic(), "2026-01-01T00:00:00+00:00") == []


def test_disconnected_condition() -> None:
    """A failed mocked probe should produce an internet issue with evidence."""
    issues = detect_network_issues(
        _diagnostic(internet_connected=False, latency_ms=None),
        "2026-01-01T00:00:00+00:00",
    )
    assert [issue["code"] for issue in issues] == ["NO_INTERNET_CONNECTION"]
    assert issues[0]["evidence"]
    assert issues[0]["detected_at"] == "2026-01-01T00:00:00+00:00"


def test_timeout_condition() -> None:
    """A simulated timeout should not be mislabeled as a generic failure."""
    issues = detect_network_issues(
        _diagnostic(internet_connected=False, timed_out=True, latency_ms=None)
    )
    assert [issue["code"] for issue in issues] == ["CONNECTIVITY_TIMEOUT"]


def test_unavailable_interface_condition() -> None:
    """No interfaces should produce one clear root-cause issue."""
    issues = detect_network_issues(
        _diagnostic(
            active_interfaces=[], internet_connected=False, latency_ms=None
        )
    )
    assert [issue["code"] for issue in issues] == ["NO_ACTIVE_INTERFACE"]
    assert issues[0]["severity"] == "high"


def test_high_latency_condition() -> None:
    """Latency above the configured simulated threshold should be detected."""
    issues = detect_network_issues(_diagnostic(latency_ms=250.0))
    assert [issue["code"] for issue in issues] == ["HIGH_LATENCY"]
    assert "250.00 ms" in issues[0]["evidence"]

