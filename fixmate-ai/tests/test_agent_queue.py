"""Offline upload queue safety and retry tests."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from fixmate_agent.client import AgentClientError
from fixmate_agent.config import AgentConfig, clean_queue_dir
from fixmate_agent.queue import QueueError, UploadQueue
from fixmate_agent.runner import flush_upload_queue, run_once, run_queue_command, run_scheduled


def _config(queue_dir: Path, token: str = "raw-device-token") -> AgentConfig:
    return AgentConfig(
        server_url="http://127.0.0.1:8000",
        device_id="device-queue-001",
        device_name="Synthetic Queue Endpoint",
        device_token=token,
        timeout_seconds=0.2,
        queue_dir=queue_dir,
    )


def _scan(config: AgentConfig) -> dict:
    return {
        "device_id": config.device_id,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "agent_version": "1.0.0",
        "health_score": 80,
        "system": {"operating_system": "Test", "platform": "test"},
        "network": {"internet_connected": False},
        "issues": [{"evidence": "alice@example.com C:\\Users\\Alice\\secret.txt"}],
    }


def test_server_failure_queues_all_uploads_without_token(tmp_path) -> None:
    class OfflineClient:
        def __init__(self, *args):
            pass

        def post(self, path, payload):
            raise AgentClientError("offline")

    queue_dir = tmp_path / "queue"
    assert run_once(
        _config(queue_dir), io.StringIO(), io.StringIO(), _scan, OfflineClient
    ) == 1
    files = sorted(queue_dir.glob("queue-*.json"))
    assert len(files) == 3
    rendered = "".join(path.read_text(encoding="utf-8") for path in files)
    assert "raw-device-token" not in rendered
    assert "alice@example.com" not in rendered
    assert "C:\\\\Users" not in rendered


def test_queue_retry_deletes_only_successful_entries(tmp_path) -> None:
    queue = UploadQueue(tmp_path / "queue")
    queue.enqueue("/api/v1/agent/heartbeat", {"device_id": "device-001"})
    queue.enqueue("/api/v1/agent/scans", {"device_id": "device-001"})

    class SuccessClient:
        def post(self, path, payload):
            return {}

    uploaded, failed = flush_upload_queue(
        queue, SuccessClient(), io.StringIO(), io.StringIO()
    )
    assert (uploaded, failed) == (2, 0)
    assert queue.entries() == []


def test_failed_retry_retains_entry(tmp_path) -> None:
    queue = UploadQueue(tmp_path / "queue")
    queue.enqueue("/api/v1/agent/heartbeat", {"device_id": "device-001"})

    class OfflineClient:
        def post(self, path, payload):
            raise AgentClientError("offline")

    assert flush_upload_queue(
        queue, OfflineClient(), io.StringIO(), io.StringIO()
    ) == (0, 1)
    assert len(queue.entries()) == 1


def test_corrupted_queue_entry_is_safe_and_retained(tmp_path) -> None:
    queue = UploadQueue(tmp_path / "queue")
    queue.directory.mkdir(parents=True)
    corrupted = queue.directory / "queue-000-corrupt.json"
    corrupted.write_text("not json", encoding="utf-8")
    status = queue.status()
    assert status.corrupted == 1

    class Client:
        def post(self, path, payload):
            raise AssertionError("corrupted payload must not be uploaded")

    assert flush_upload_queue(queue, Client(), io.StringIO(), io.StringIO()) == (0, 1)
    assert corrupted.exists()


def test_queue_rejects_traversal_unknown_endpoints_and_file_overflow(tmp_path) -> None:
    with pytest.raises(ValueError, match="traversal"):
        clean_queue_dir(tmp_path / "safe" / ".." / "escape")
    queue = UploadQueue(tmp_path / "queue", max_files=1)
    with pytest.raises(QueueError, match="not allowed"):
        queue.enqueue("/api/v1/arbitrary", {})
    queue.enqueue("/api/v1/agent/heartbeat", {"device_id": "device-001"})
    with pytest.raises(QueueError, match="limit"):
        queue.enqueue("/api/v1/agent/scans", {"device_id": "device-001"})


def test_sensitive_keys_are_removed_from_queue_files(tmp_path) -> None:
    queue = UploadQueue(tmp_path / "queue")
    path = queue.enqueue(
        "/api/v1/agent/scans",
        {
            "device_id": "device-001",
            "token": "raw-token",
            "nested": {"password": "raw-password", "safe": "value"},
        },
    )
    content = path.read_text(encoding="utf-8")
    assert "raw-token" not in content
    assert "raw-password" not in content
    endpoint, payload = queue.read(path)
    assert endpoint.endswith("/scans")
    assert payload["nested"] == {"safe": "value"}


def test_queue_status_and_explicit_flush_commands(tmp_path) -> None:
    queue_dir = tmp_path / "queue"
    queue = UploadQueue(queue_dir)
    queue.enqueue("/api/v1/agent/heartbeat", {"device_id": "device-001"})
    output = io.StringIO()
    assert run_queue_command(
        AgentConfig(
            server_url="http://127.0.0.1:8000",
            device_id="device-001",
            device_name="Synthetic",
            device_token="",
            queue_dir=queue_dir,
            queue_status=True,
        ),
        output,
        io.StringIO(),
    ) == 0
    assert "1 valid" in output.getvalue()

    class Client:
        def __init__(self, *args):
            pass

        def post(self, path, payload):
            return {}

    assert run_queue_command(
        AgentConfig(
            server_url="http://127.0.0.1:8000",
            device_id="device-001",
            device_name="Synthetic",
            device_token="token",
            queue_dir=queue_dir,
            flush_queue=True,
        ),
        io.StringIO(),
        io.StringIO(),
        Client,
    ) == 0
    assert UploadQueue(queue_dir).entries() == []


def test_scheduled_mode_retries_existing_queue(tmp_path) -> None:
    queue_dir = tmp_path / "queue"
    UploadQueue(queue_dir).enqueue(
        "/api/v1/agent/heartbeat", {"device_id": "device-queue-001"}
    )
    posted = []

    class Client:
        def __init__(self, *args):
            pass

        def post(self, path, payload):
            posted.append(path)
            return {}

    assert (
        run_scheduled(
            AgentConfig(
                server_url="http://127.0.0.1:8000",
                device_id="device-queue-001",
                device_name="Synthetic",
                device_token="token",
                queue_dir=queue_dir,
                heartbeat_only=True,
                max_iterations=1,
            ),
            io.StringIO(),
            io.StringIO(),
            client_factory=Client,
        )
        == 0
    )
    assert posted.count("/api/v1/agent/heartbeat") == 2
    assert UploadQueue(queue_dir).entries() == []
