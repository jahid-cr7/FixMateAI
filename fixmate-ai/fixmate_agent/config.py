"""Environment and command-line configuration for the endpoint agent."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse

DEVICE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
DEFAULT_QUEUE_DIR = Path.home() / ".fixmate-ai" / "queue"


def derived_device_id() -> str:
    """Create a stable opaque local ID without transmitting the hostname."""
    source = f"{platform.node()}|{platform.system()}|{platform.machine()}"
    digest = hashlib.sha256(source.encode("utf-8", errors="ignore")).hexdigest()[:20]
    return f"device-{digest}"


def default_device_name(device_id: str) -> str:
    """Return a generic name that does not expose the local hostname."""
    return f"Endpoint-{device_id[-6:].upper()}"


def clean_server_url(value: str) -> str:
    """Validate an HTTP(S) API base URL without credentials or extra paths."""
    cleaned = value.strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("server URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("server URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("server URL must not contain a query or fragment")
    return cleaned


def clean_queue_dir(value: str | Path) -> Path:
    """Resolve an explicit queue directory while rejecting traversal and roots."""
    candidate = Path(value).expanduser()
    if ".." in candidate.parts:
        raise ValueError("queue directory must not contain parent traversal")
    resolved = candidate.resolve(strict=False)
    if resolved == Path(resolved.anchor):
        raise ValueError("queue directory must not be a filesystem root")
    return resolved


def _environment_timeout(source: Mapping[str, str]) -> float:
    try:
        return float(source.get("FIXMATE_AGENT_TIMEOUT_SECONDS", 5.0))
    except (TypeError, ValueError):
        return 5.0


def _environment_interval(source: Mapping[str, str]) -> float | None:
    value = source.get("FIXMATE_AGENT_INTERVAL_SECONDS", "").strip()
    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


@dataclass(frozen=True)
class AgentConfig:
    """Validated agent settings; token is hidden from representations."""

    server_url: str
    device_id: str
    device_name: str
    device_token: str = field(repr=False)
    timeout_seconds: float = 5.0
    dry_run: bool = False
    network_host: str = "1.1.1.1"
    network_port: int = 443
    queue_dir: Path = DEFAULT_QUEUE_DIR
    max_queue_files: int = 100
    queue_status: bool = False
    flush_queue: bool = False
    once: bool = False
    interval_seconds: float | None = None
    heartbeat_only: bool = False
    max_iterations: int | None = None


def parse_agent_config(
    argv: list[str] | None = None,
    environment: Mapping[str, str] | None = None,
) -> AgentConfig:
    """Parse CLI options over environment values over safe defaults."""
    source = os.environ if environment is None else environment
    default_id = source.get("FIXMATE_DEVICE_ID", "").strip() or derived_device_id()
    parser = argparse.ArgumentParser(
        description="Run the privacy-safe FixMate AI endpoint agent."
    )
    parser.add_argument(
        "--server",
        default=(
            source.get("FIXMATE_AGENT_SERVER_URL")
            or source.get("FIXMATE_SERVER_URL")
            or "http://127.0.0.1:8000"
        ),
    )
    parser.add_argument("--device-id", default=default_id)
    parser.add_argument(
        "--device-name",
        default=source.get("FIXMATE_DEVICE_NAME", ""),
    )
    parser.add_argument("--timeout", type=float, default=_environment_timeout(source))
    parser.add_argument("--network-host", default="1.1.1.1")
    parser.add_argument("--network-port", type=int, default=443)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--queue-dir",
        default=(
            source.get("FIXMATE_AGENT_QUEUE_DIR", "").strip()
            or str(DEFAULT_QUEUE_DIR)
        ),
    )
    parser.add_argument("--max-queue-files", type=int, default=100)
    commands = parser.add_mutually_exclusive_group()
    commands.add_argument("--queue-status", action="store_true")
    commands.add_argument("--flush-queue", action="store_true")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run exactly one cycle and exit. This is also the default when no interval is set.",
    )
    interval_group = parser.add_mutually_exclusive_group()
    interval_group.add_argument(
        "--interval-seconds",
        type=float,
        default=_environment_interval(source),
        help="Run repeatedly with this many seconds between cycles.",
    )
    interval_group.add_argument(
        "--interval-minutes",
        type=float,
        help="Run repeatedly with this many minutes between cycles.",
    )
    parser.add_argument(
        "--heartbeat-only",
        action="store_true",
        help="Send heartbeat cycles without collecting or uploading scan diagnostics.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        help="Stop after this many cycles; useful for tests and demos.",
    )
    arguments = parser.parse_args(argv)
    try:
        server_url = clean_server_url(arguments.server)
        queue_dir = clean_queue_dir(arguments.queue_dir)
    except ValueError as error:
        parser.error(str(error))
    if not 0.1 <= arguments.timeout <= 30:
        parser.error("--timeout must be between 0.1 and 30 seconds")
    if not 1 <= arguments.network_port <= 65535:
        parser.error("--network-port must be between 1 and 65535")
    if not 1 <= arguments.max_queue_files <= 10_000:
        parser.error("--max-queue-files must be between 1 and 10000")
    if arguments.dry_run and (arguments.queue_status or arguments.flush_queue):
        parser.error("--dry-run cannot be combined with queue commands")
    if arguments.dry_run and (
        arguments.interval_seconds
        or arguments.interval_minutes
        or arguments.heartbeat_only
        or arguments.max_iterations
    ):
        parser.error("--dry-run cannot be combined with scheduled or heartbeat-only mode")
    if (arguments.queue_status or arguments.flush_queue) and (
        arguments.interval_seconds
        or arguments.interval_minutes
        or arguments.heartbeat_only
        or arguments.max_iterations
        or arguments.once
    ):
        parser.error("queue commands cannot be combined with run-mode options")
    interval_seconds = arguments.interval_seconds
    if arguments.interval_minutes is not None:
        interval_seconds = arguments.interval_minutes * 60
    if interval_seconds is not None and not 1 <= interval_seconds <= 86_400:
        parser.error("interval must be between 1 second and 24 hours")
    if arguments.max_iterations is not None and not 1 <= arguments.max_iterations <= 10_000:
        parser.error("--max-iterations must be between 1 and 10000")
    device_id = arguments.device_id.strip()
    if not DEVICE_ID_PATTERN.fullmatch(device_id):
        parser.error(
            "--device-id must contain 3 to 64 letters, numbers, dots, underscores, or hyphens"
        )
    name = (arguments.device_name or default_device_name(device_id)).strip()
    if not name or len(name) > 100:
        parser.error("--device-name must contain 1 to 100 characters")
    return AgentConfig(
        server_url=server_url,
        device_id=device_id,
        device_name=name,
        device_token=source.get("FIXMATE_DEVICE_TOKEN", ""),
        timeout_seconds=arguments.timeout,
        dry_run=arguments.dry_run,
        network_host=arguments.network_host.strip() or "1.1.1.1",
        network_port=arguments.network_port,
        queue_dir=queue_dir,
        max_queue_files=arguments.max_queue_files,
        queue_status=arguments.queue_status,
        flush_queue=arguments.flush_queue,
        once=arguments.once,
        interval_seconds=interval_seconds,
        heartbeat_only=arguments.heartbeat_only,
        max_iterations=arguments.max_iterations,
    )
