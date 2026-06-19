"""Safe, cross-platform collection of basic network diagnostics."""

from __future__ import annotations

import ipaddress
import socket
import time
from datetime import datetime
from typing import Any, TypedDict

import psutil

MIN_TIMEOUT_SECONDS = 0.1
MAX_TIMEOUT_SECONDS = 5.0


class NetworkDiagnostic(TypedDict):
    """A single read-only network diagnostic result."""

    collected_at: str
    target_host: str
    target_port: int
    timeout_seconds: float
    latency_threshold_ms: float
    active_interfaces: list[str]
    connection_status: bool
    internet_connected: bool
    timed_out: bool
    latency_ms: float | None
    bytes_sent: int | None
    bytes_received: int | None


def _is_non_loopback_ip(address: str) -> bool:
    """Return whether an address is a usable non-loopback IP address."""
    try:
        normalized = address.split("%", maxsplit=1)[0]
        return not ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def get_active_interfaces() -> list[str]:
    """Return active interface names without exposing hardware addresses."""
    try:
        statistics = psutil.net_if_stats()
        addresses = psutil.net_if_addrs()
    except (OSError, RuntimeError, psutil.Error):
        return []

    active: list[str] = []
    for name, stats in statistics.items():
        if not stats.isup:
            continue
        interface_addresses = addresses.get(name, [])
        has_usable_ip = any(
            item.family in (socket.AF_INET, socket.AF_INET6)
            and _is_non_loopback_ip(item.address)
            for item in interface_addresses
        )
        if has_usable_ip:
            active.append(name)
    return sorted(active, key=str.casefold)


def _network_io() -> tuple[int | None, int | None]:
    """Return cumulative sent and received byte counters when available."""
    try:
        counters = psutil.net_io_counters()
    except (OSError, RuntimeError, psutil.Error):
        return None, None
    if counters is None:
        return None, None
    return int(counters.bytes_sent), int(counters.bytes_recv)


def test_connectivity(
    host: str,
    port: int,
    timeout_seconds: float,
) -> tuple[bool, bool, float | None]:
    """Test a TCP connection and return connected, timed-out, and latency values."""
    timeout = max(MIN_TIMEOUT_SECONDS, min(float(timeout_seconds), MAX_TIMEOUT_SECONDS))
    started = time.perf_counter()
    connection: Any | None = None
    try:
        connection = socket.create_connection((host, port), timeout=timeout)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return True, False, latency_ms
    except (socket.timeout, TimeoutError):
        return False, True, None
    except (OSError, ValueError):
        return False, False, None
    finally:
        if connection is not None:
            try:
                connection.close()
            except OSError:
                pass


def collect_network_diagnostic(
    host: str = "1.1.1.1",
    port: int = 443,
    timeout_seconds: float = 1.5,
    latency_threshold_ms: float = 150.0,
) -> NetworkDiagnostic:
    """Collect interface, traffic, connectivity, and latency information safely."""
    clean_host = host.strip() or "1.1.1.1"
    clean_port = max(1, min(int(port), 65535))
    clean_timeout = max(
        MIN_TIMEOUT_SECONDS,
        min(float(timeout_seconds), MAX_TIMEOUT_SECONDS),
    )
    clean_threshold = max(1.0, float(latency_threshold_ms))
    active_interfaces = get_active_interfaces()
    bytes_sent, bytes_received = _network_io()

    if active_interfaces:
        internet_connected, timed_out, latency_ms = test_connectivity(
            clean_host,
            clean_port,
            clean_timeout,
        )
    else:
        internet_connected, timed_out, latency_ms = False, False, None

    return {
        "collected_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "target_host": clean_host,
        "target_port": clean_port,
        "timeout_seconds": clean_timeout,
        "latency_threshold_ms": clean_threshold,
        "active_interfaces": active_interfaces,
        "connection_status": bool(active_interfaces),
        "internet_connected": internet_connected,
        "timed_out": timed_out,
        "latency_ms": latency_ms,
        "bytes_sent": bytes_sent,
        "bytes_received": bytes_received,
    }

