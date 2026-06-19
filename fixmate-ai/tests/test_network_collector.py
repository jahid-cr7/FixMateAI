"""Mocked tests for safe network collection."""

from __future__ import annotations

import socket
from types import SimpleNamespace

import pytest

from src import network_collector


class FakeConnection:
    """Minimal socket-like object used by connectivity tests."""

    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        """Record that the collector closed the connection."""
        self.closed = True


def _mock_active_interface(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide one active interface without using the real computer."""
    monkeypatch.setattr(
        network_collector.psutil,
        "net_if_stats",
        lambda: {"Ethernet": SimpleNamespace(isup=True)},
    )
    monkeypatch.setattr(
        network_collector.psutil,
        "net_if_addrs",
        lambda: {
            "Ethernet": [
                SimpleNamespace(family=socket.AF_INET, address="192.0.2.10")
            ]
        },
    )
    monkeypatch.setattr(
        network_collector.psutil,
        "net_io_counters",
        lambda: SimpleNamespace(bytes_sent=1024, bytes_recv=2048),
    )


def test_connected_diagnostic_uses_mocked_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful mocked connection should include latency and traffic."""
    _mock_active_interface(monkeypatch)
    connection = FakeConnection()
    monkeypatch.setattr(
        network_collector.socket,
        "create_connection",
        lambda address, timeout: connection,
    )
    clock = iter([10.0, 10.025])
    monkeypatch.setattr(network_collector.time, "perf_counter", lambda: next(clock))

    diagnostic = network_collector.collect_network_diagnostic()

    assert diagnostic["active_interfaces"] == ["Ethernet"]
    assert diagnostic["connection_status"] is True
    assert diagnostic["internet_connected"] is True
    assert diagnostic["latency_ms"] == pytest.approx(25.0)
    assert diagnostic["bytes_sent"] == 1024
    assert diagnostic["bytes_received"] == 2048
    assert connection.closed is True


def test_disconnected_diagnostic_handles_os_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A refused mocked connection should be reported without crashing."""
    _mock_active_interface(monkeypatch)

    def refuse_connection(address: object, timeout: float) -> None:
        raise OSError("simulated offline computer")

    monkeypatch.setattr(
        network_collector.socket, "create_connection", refuse_connection
    )
    monkeypatch.setattr(network_collector.time, "perf_counter", lambda: 10.0)

    diagnostic = network_collector.collect_network_diagnostic()

    assert diagnostic["connection_status"] is True
    assert diagnostic["internet_connected"] is False
    assert diagnostic["timed_out"] is False
    assert diagnostic["latency_ms"] is None


def test_timeout_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    """A mocked socket timeout should be distinguishable from other failures."""
    _mock_active_interface(monkeypatch)

    def time_out(address: object, timeout: float) -> None:
        raise socket.timeout("simulated timeout")

    monkeypatch.setattr(network_collector.socket, "create_connection", time_out)
    monkeypatch.setattr(network_collector.time, "perf_counter", lambda: 10.0)

    diagnostic = network_collector.collect_network_diagnostic(timeout_seconds=0.5)

    assert diagnostic["internet_connected"] is False
    assert diagnostic["timed_out"] is True
    assert diagnostic["timeout_seconds"] == 0.5


def test_unavailable_interfaces_skip_connectivity_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unavailable interface metrics should produce a safe disconnected result."""
    monkeypatch.setattr(
        network_collector.psutil,
        "net_if_stats",
        lambda: (_ for _ in ()).throw(OSError("unavailable")),
    )
    monkeypatch.setattr(
        network_collector.psutil,
        "net_io_counters",
        lambda: None,
    )

    def unexpected_probe(address: object, timeout: float) -> None:
        raise AssertionError("connectivity must not run without an active interface")

    monkeypatch.setattr(
        network_collector.socket, "create_connection", unexpected_probe
    )

    diagnostic = network_collector.collect_network_diagnostic()

    assert diagnostic["active_interfaces"] == []
    assert diagnostic["connection_status"] is False
    assert diagnostic["bytes_sent"] is None
    assert diagnostic["bytes_received"] is None


def test_loopback_interface_is_not_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Loopback-only interfaces are not active external network connections."""
    monkeypatch.setattr(
        network_collector.psutil,
        "net_if_stats",
        lambda: {"Loopback": SimpleNamespace(isup=True)},
    )
    monkeypatch.setattr(
        network_collector.psutil,
        "net_if_addrs",
        lambda: {
            "Loopback": [SimpleNamespace(family=socket.AF_INET, address="127.0.0.1")]
        },
    )
    assert network_collector.get_active_interfaces() == []

