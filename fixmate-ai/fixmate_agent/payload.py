"""Privacy-minimized payload construction using existing collectors and rules."""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timezone
from typing import Any, Callable

from fixmate_agent import AGENT_VERSION
from fixmate_agent.config import AgentConfig
from src.collector import collect_system_metrics
from src.detector import detect_issues
from src.health_score import calculate_health_score
from src.network_collector import collect_network_diagnostic
from src.network_detector import detect_network_issues
from src.privacy import redact_sensitive_text


def _redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive_text(value)
    if isinstance(value, dict):
        return {str(key): _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def build_scan_payload(
    config: AgentConfig,
    system_collector: Callable[[], dict[str, Any]] = collect_system_metrics,
    network_collector: Callable[..., dict[str, Any]] = collect_network_diagnostic,
) -> dict[str, Any]:
    """Collect one scan and omit process names, interfaces, addresses, and targets."""
    system = system_collector()
    network = network_collector(
        host=config.network_host,
        port=config.network_port,
        timeout_seconds=min(config.timeout_seconds, 5.0),
    )
    system_issues = detect_issues(
        system.get("cpu_percent"),
        system.get("memory_percent"),
        system.get("disk_free_percent"),
    )
    network_issues = detect_network_issues(
        network, detected_at=str(network.get("collected_at"))
    )
    issues: list[dict[str, Any]] = []
    for issue in system_issues:
        issues.append(
            {
                "source": "system",
                "code": issue["code"],
                "severity": issue["severity"],
                "evidence": f"{issue['metric']}: {issue['value']:.1f}%",
                "explanation": issue["explanation"],
                "recommendation": issue["recommendation"],
            }
        )
    for issue in network_issues:
        issues.append(
            {
                "source": "network",
                "code": issue["code"],
                "severity": issue["severity"],
                "evidence": issue["evidence"],
                "explanation": issue["explanation"],
                "recommendation": issue["recommendation"],
            }
        )
    timestamp = str(system.get("collected_at") or datetime.now(timezone.utc).isoformat())
    payload = {
        "device_id": config.device_id,
        "timestamp": timestamp,
        "agent_version": AGENT_VERSION,
        "health_score": calculate_health_score(issues),
        "system": {
            "operating_system": str(system.get("os_name") or "Unknown"),
            "platform": sys.platform,
            "cpu_percent": system.get("cpu_percent"),
            "memory_percent": system.get("memory_percent"),
            "disk_used_percent": system.get("disk_used_percent"),
            "disk_free_percent": system.get("disk_free_percent"),
            "boot_time": system.get("boot_time"),
        },
        "network": {
            "connection_status": bool(network.get("connection_status")),
            "internet_connected": bool(network.get("internet_connected")),
            "timed_out": bool(network.get("timed_out")),
            "latency_ms": network.get("latency_ms"),
            "bytes_sent": network.get("bytes_sent"),
            "bytes_received": network.get("bytes_received"),
            "active_interface_count": len(network.get("active_interfaces") or []),
        },
        "issues": issues,
    }
    return _redact(payload)


def registration_payload(config: AgentConfig, scan: dict[str, Any]) -> dict[str, Any]:
    """Build registration metadata without hostname, token, or hardware address."""
    return _redact(
        {
            "device_id": config.device_id,
            "display_name": config.device_name,
            "operating_system": scan["system"]["operating_system"],
            "platform": platform.system() or scan["system"]["platform"],
            "agent_version": AGENT_VERSION,
            "timestamp": scan["timestamp"],
        }
    )


def heartbeat_payload(config: AgentConfig, scan: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal heartbeat from the same one-shot collection time."""
    return {
        "device_id": config.device_id,
        "timestamp": scan["timestamp"],
        "status": "online",
        "agent_version": AGENT_VERSION,
    }
