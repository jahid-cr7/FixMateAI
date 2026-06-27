"""One-shot endpoint-agent privacy, transport, and failure tests."""

from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.error import URLError

import pytest

from fixmate_agent.client import AgentClient, AgentClientError
from fixmate_agent.config import AgentConfig, parse_agent_config
from fixmate_agent.payload import build_scan_payload
from fixmate_agent.runner import run_once, run_scheduled


def _config(**changes) -> AgentConfig:
    values = {
        "server_url": "http://127.0.0.1:8000",
        "device_id": "device-test-001",
        "device_name": "Synthetic Endpoint",
        "device_token": "secret-device-token",
        "timeout_seconds": 0.5,
        "dry_run": False,
        "queue_dir": Path("test-agent-queue").resolve(),
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


def test_agent_config_uses_environment_and_hides_token(tmp_path) -> None:
    config = parse_agent_config(
        ["--dry-run", "--device-id", "device-test-001"],
        {
            "FIXMATE_DEVICE_TOKEN": "never-print-this",
            "FIXMATE_AGENT_QUEUE_DIR": str(tmp_path / "queue"),
        },
    )
    assert config.dry_run is True
    assert config.queue_dir == (tmp_path / "queue").resolve()
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


def test_runner_dry_run_needs_no_token_and_uploads_in_order(tmp_path) -> None:
    output, errors = io.StringIO(), io.StringIO()
    assert run_once(
        _config(device_token="", dry_run=True, queue_dir=tmp_path / "queue"),
        output,
        errors,
        _scan,
    ) == 0
    assert "device-test-001" in output.getvalue()
    assert not (tmp_path / "queue").exists()

    paths = []

    class Client:
        def __init__(self, *args):
            pass

        def post(self, path, payload):
            paths.append(path)
            return {}

    assert run_once(
        _config(queue_dir=tmp_path / "queue"),
        io.StringIO(),
        io.StringIO(),
        _scan,
        Client,
    ) == 0
    assert paths == [
        "/api/v1/agent/register",
        "/api/v1/agent/heartbeat",
        "/api/v1/agent/scans",
    ]


def test_cli_priority_and_environment_configuration(tmp_path) -> None:
    config = parse_agent_config(
        [
            "--server",
            "http://127.0.0.1:9000",
            "--timeout",
            "2",
            "--queue-dir",
            str(tmp_path / "cli-queue"),
        ],
        {
            "FIXMATE_AGENT_SERVER_URL": "http://127.0.0.1:8002",
            "FIXMATE_SERVER_URL": "http://127.0.0.1:8001",
            "FIXMATE_AGENT_TIMEOUT_SECONDS": "4",
            "FIXMATE_DEVICE_NAME": "Environment Endpoint",
            "FIXMATE_AGENT_INTERVAL_SECONDS": "9",
            "FIXMATE_AGENT_QUEUE_DIR": str(tmp_path / "environment-queue"),
        },
    )
    assert config.server_url == "http://127.0.0.1:9000"
    assert config.timeout_seconds == 2
    assert config.queue_dir == (tmp_path / "cli-queue").resolve()

    environment_config = parse_agent_config(
        [],
        {
            "FIXMATE_AGENT_SERVER_URL": "http://127.0.0.1:8002",
            "FIXMATE_SERVER_URL": "http://127.0.0.1:8001",
            "FIXMATE_AGENT_TIMEOUT_SECONDS": "4",
            "FIXMATE_DEVICE_NAME": "Environment Endpoint",
            "FIXMATE_AGENT_INTERVAL_SECONDS": "9",
            "FIXMATE_AGENT_QUEUE_DIR": str(tmp_path / "environment-queue"),
        },
    )
    assert environment_config.server_url == "http://127.0.0.1:8002"
    assert environment_config.device_name == "Environment Endpoint"
    assert environment_config.timeout_seconds == 4
    assert environment_config.interval_seconds == 9


def test_scheduled_runner_uses_max_iterations_and_retries_queue(tmp_path) -> None:
    output, errors = io.StringIO(), io.StringIO()
    posted = []
    sleeps = []

    class Client:
        def __init__(self, *args):
            pass

        def post(self, path, payload):
            posted.append(path)
            return {}

    result = run_scheduled(
        _config(queue_dir=tmp_path / "queue", interval_seconds=10, max_iterations=3),
        output,
        errors,
        _scan,
        Client,
        sleeper=lambda seconds: sleeps.append(seconds),
    )
    assert result == 0
    assert posted[0] == "/api/v1/agent/register"
    assert posted.count("/api/v1/agent/heartbeat") == 3
    assert posted.count("/api/v1/agent/scans") == 3
    assert sleeps == [10, 10]
    assert "Completed 3 scheduled cycle" in output.getvalue()


def test_heartbeat_only_sends_no_scan(tmp_path) -> None:
    posted = []

    class Client:
        def __init__(self, *args):
            pass

        def post(self, path, payload):
            posted.append(path)
            return {}

    assert (
        run_scheduled(
            _config(queue_dir=tmp_path / "queue", heartbeat_only=True, max_iterations=1),
            io.StringIO(),
            io.StringIO(),
            _scan,
            Client,
        )
        == 0
    )
    assert "/api/v1/agent/register" in posted
    assert "/api/v1/agent/heartbeat" in posted
    assert "/api/v1/agent/scans" not in posted


def test_failed_upload_does_not_crash_scheduled_runner(tmp_path) -> None:
    calls = []

    class SometimesOfflineClient:
        def __init__(self, *args):
            pass

        def post(self, path, payload):
            calls.append(path)
            if path.endswith("/heartbeat"):
                raise AgentClientError("offline")
            return {}

    result = run_scheduled(
        _config(queue_dir=tmp_path / "queue", interval_seconds=1, max_iterations=2),
        io.StringIO(),
        io.StringIO(),
        _scan,
        SometimesOfflineClient,
        sleeper=lambda _: None,
    )
    assert result == 1
    assert calls.count("/api/v1/agent/heartbeat") >= 2
    assert calls.count("/api/v1/agent/scans") == 2


def test_scheduled_runner_handles_ctrl_c_cleanly(tmp_path) -> None:
    class Client:
        def __init__(self, *args):
            pass

        def post(self, path, payload):
            return {}

    def interrupted_sleep(seconds):
        raise KeyboardInterrupt

    output = io.StringIO()
    result = run_scheduled(
        _config(queue_dir=tmp_path / "queue", interval_seconds=10),
        output,
        io.StringIO(),
        _scan,
        Client,
        sleeper=interrupted_sleep,
    )
    assert result == 130
    assert "Ctrl+C" in output.getvalue()
