"""Environment and command-line configuration for the one-shot agent."""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import re
import sys
from dataclasses import dataclass, field
from typing import Mapping
from urllib.parse import urlparse

DEVICE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")


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


@dataclass(frozen=True)
class AgentConfig:
    """Validated one-shot agent settings; token is hidden from representations."""

    server_url: str
    device_id: str
    device_name: str
    device_token: str = field(repr=False)
    timeout_seconds: float = 5.0
    dry_run: bool = False
    network_host: str = "1.1.1.1"
    network_port: int = 443


def parse_agent_config(
    argv: list[str] | None = None,
    environment: Mapping[str, str] | None = None,
) -> AgentConfig:
    """Parse CLI options and the device token environment variable."""
    source = os.environ if environment is None else environment
    default_id = source.get("FIXMATE_DEVICE_ID", "").strip() or derived_device_id()
    parser = argparse.ArgumentParser(
        description="Run one privacy-safe FixMate AI endpoint scan and exit."
    )
    parser.add_argument(
        "--server",
        default=source.get("FIXMATE_SERVER_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument("--device-id", default=default_id)
    parser.add_argument("--device-name")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--network-host", default="1.1.1.1")
    parser.add_argument("--network-port", type=int, default=443)
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        server_url = clean_server_url(arguments.server)
    except ValueError as error:
        parser.error(str(error))
    if not 0.1 <= arguments.timeout <= 30:
        parser.error("--timeout must be between 0.1 and 30 seconds")
    if not 1 <= arguments.network_port <= 65535:
        parser.error("--network-port must be between 1 and 65535")
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
    )
