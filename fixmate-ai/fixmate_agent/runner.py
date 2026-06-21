"""One-shot endpoint-agent orchestration with deterministic exit behavior."""

from __future__ import annotations

import json
from typing import Callable, TextIO

from fixmate_agent.client import AgentClient, AgentClientError
from fixmate_agent.config import AgentConfig
from fixmate_agent.payload import (
    build_scan_payload,
    heartbeat_payload,
    registration_payload,
)


def run_once(
    config: AgentConfig,
    output: TextIO,
    error_output: TextIO,
    payload_builder: Callable[[AgentConfig], dict] = build_scan_payload,
    client_factory: Callable[..., AgentClient] = AgentClient,
) -> int:
    """Collect once, optionally print, otherwise register/heartbeat/upload and exit."""
    scan = payload_builder(config)
    if config.dry_run:
        print(json.dumps(scan, indent=2, sort_keys=True), file=output)
        return 0
    if not config.device_token:
        print(
            "FIXMATE_DEVICE_TOKEN is required unless --dry-run is used.",
            file=error_output,
        )
        return 2
    client = client_factory(
        config.server_url, config.device_token, config.timeout_seconds
    )
    try:
        client.post("/api/v1/agent/register", registration_payload(config, scan))
        client.post("/api/v1/agent/heartbeat", heartbeat_payload(config, scan))
        client.post("/api/v1/agent/scans", scan)
    except AgentClientError as error:
        print(str(error), file=error_output)
        return 1
    print(f"Uploaded one diagnostic batch for {config.device_name}.", file=output)
    return 0
