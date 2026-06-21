"""One-shot endpoint-agent privacy, transport, and failure tests."""

from __future__ import annotations

import io
import json
from urllib.error import URLError

import pytest

from fixmate_agent.client import AgentClient, AgentClientError
from fixmate_agent.config import AgentConfig, parse_agent_config
from fixmate_agent.payload import build_scan_payload
from fixmate_agent.runner import run_once


def _config(**changes) -> AgentConfig:
    values = {
        "server_url": "http://127.0.0.1:8000",
        "device_id": "device-test-001",
        "device_name": "Synthetic Endpoint",
        "device_token": "secret-device-token",
        "timeout_seconds": 0.5,
        "dry_run": False,
    }
    values.update(changes)
    return AgentConfig(**values)


def _scan(config: AgentConfig) -> dict:
    return {
        "device_id": config.device_id,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "agent_version": "1.0.0",
        "health_score": 100,
        "system": {"operating_system": "Synthetic OS", "platform": "test"},
        "network": {"internet_connected": True},
        "issues": [],
    }


def test_agent_config_uses_environment_and_hides_token() -> None:
    config = parse_agent_config(
        ["--dry-run", "--device-id", "device-test-001"],
        {"FIXMATE_DEVICE_TOKEN": "never-print-this"},
    )
    assert config.dry_run is True
    assert "never-print-this" not in repr(config)
    with pytest.raises(SystemExit):
        parse_agent_config(["--device-id", "../unsafe"], {})


def test_payload_reuses_collectors_but_omits_private_detail() -> None:
    system = lambda: {
        "collected_at": "2026-01-01T00:00:00+00:00",
        "os_name": "Ubuntu",
        "cpu_percent": 10,
        "memory_percent": 20,
        "disk_used_percent": 30,
        "disk_free_percent": 70,
        "boot_time": None,
        "top_processes": [{"name": "private-process"}],
    }
    network = lambda **_: {
        "collected_at": "2026-01-01T00:00:00+00:00",
        "connection_status": True,
        "internet_connected": True,
        "timed_out": False,
        "latency_ms": 12,
        "bytes_sent": 100,
        "bytes_received": 200,
        "active_interfaces": ["Private VPN"],
    }
    payload = build_scan_payload(_config(), system, network)
    rendered = json.dumps(payload)
    assert "private-process" not in rendered
    assert "Private VPN" not in rendered
    assert payload["network"]["active_interface_count"] == 1


def test_client_sets_device_header_and_handles_unavailable_server() -> None:
    captured = {}

    class Response:
        def read(self):
            return b'{"ok": true}'

        def close(self):
            return None

    def opener(request, timeout):
        captured["header"] = request.get_header("X-device-token")
        captured["timeout"] = timeout
        return Response()

    assert AgentClient("http://localhost", "token", 0.5, opener).post("/x", {}) == {"ok": True}
    assert captured == {"header": "token", "timeout": 0.5}

    def unavailable(*_, **__):
        raise URLError("offline")

    with pytest.raises(AgentClientError, match="unavailable"):
        AgentClient("http://localhost", "token", 0.5, unavailable).post("/x", {})


def test_runner_dry_run_needs_no_token_and_uploads_in_order() -> None:
    output, errors = io.StringIO(), io.StringIO()
    assert run_once(_config(device_token="", dry_run=True), output, errors, _scan) == 0
    assert "device-test-001" in output.getvalue()

    paths = []

    class Client:
        def __init__(self, *args):
            pass

        def post(self, path, payload):
            paths.append(path)
            return {}

    assert run_once(_config(), io.StringIO(), io.StringIO(), _scan, Client) == 0
    assert paths == [
        "/api/v1/agent/register",
        "/api/v1/agent/heartbeat",
        "/api/v1/agent/scans",
    ]

