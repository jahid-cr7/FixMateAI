"""Pure detection rules for network diagnostic results."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping, TypedDict

from src.recommendations import (
    HIGH_LATENCY_EXPLANATION,
    HIGH_LATENCY_RECOMMENDATION,
    NETWORK_TIMEOUT_EXPLANATION,
    NETWORK_TIMEOUT_RECOMMENDATION,
    NO_ACTIVE_INTERFACE_EXPLANATION,
    NO_ACTIVE_INTERFACE_RECOMMENDATION,
    NO_INTERNET_EXPLANATION,
    NO_INTERNET_RECOMMENDATION,
)


class NetworkIssue(TypedDict):
    """A network issue with evidence and safe troubleshooting guidance."""

    code: str
    severity: str
    evidence: str
    explanation: str
    recommendation: str
    detected_at: str


def detect_network_issues(
    diagnostic: Mapping[str, object],
    detected_at: str | None = None,
) -> list[NetworkIssue]:
    """Evaluate one diagnostic without performing any real network operations."""
    timestamp = detected_at or datetime.now().astimezone().isoformat(timespec="seconds")
    issues: list[NetworkIssue] = []
    active_interfaces = list(diagnostic.get("active_interfaces") or [])

    if not active_interfaces:
        issues.append(
            {
                "code": "NO_ACTIVE_INTERFACE",
                "severity": "high",
                "evidence": "No active non-loopback network interface with an IP address was found.",
                "explanation": NO_ACTIVE_INTERFACE_EXPLANATION,
                "recommendation": NO_ACTIVE_INTERFACE_RECOMMENDATION,
                "detected_at": timestamp,
            }
        )
        return issues

    host = str(diagnostic.get("target_host") or "configured host")
    port = diagnostic.get("target_port")
    target = f"{host}:{port}" if port is not None else host

    if bool(diagnostic.get("timed_out")):
        timeout = diagnostic.get("timeout_seconds")
        issues.append(
            {
                "code": "CONNECTIVITY_TIMEOUT",
                "severity": "medium",
                "evidence": f"The connection to {target} did not complete within {timeout} seconds.",
                "explanation": NETWORK_TIMEOUT_EXPLANATION,
                "recommendation": NETWORK_TIMEOUT_RECOMMENDATION,
                "detected_at": timestamp,
            }
        )
    elif not bool(diagnostic.get("internet_connected")):
        issues.append(
            {
                "code": "NO_INTERNET_CONNECTION",
                "severity": "high",
                "evidence": f"A TCP connection to {target} could not be established.",
                "explanation": NO_INTERNET_EXPLANATION,
                "recommendation": NO_INTERNET_RECOMMENDATION,
                "detected_at": timestamp,
            }
        )

    latency = diagnostic.get("latency_ms")
    threshold = diagnostic.get("latency_threshold_ms")
    if (
        isinstance(latency, (int, float))
        and isinstance(threshold, (int, float))
        and latency > threshold
    ):
        issues.append(
            {
                "code": "HIGH_LATENCY",
                "severity": "medium",
                "evidence": f"Measured latency was {latency:.2f} ms; the configured threshold is {threshold:.2f} ms.",
                "explanation": HIGH_LATENCY_EXPLANATION,
                "recommendation": HIGH_LATENCY_RECOMMENDATION,
                "detected_at": timestamp,
            }
        )

    return issues

