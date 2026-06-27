"""Endpoint-agent orchestration with one-shot, queue, and scheduled modes."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, TextIO

from fixmate_agent.client import AgentClient, AgentClientError
from fixmate_agent.config import AgentConfig
from fixmate_agent.payload import (
    build_scan_payload,
    current_heartbeat_payload,
    heartbeat_payload,
    minimal_registration_payload,
    registration_payload,
)
from fixmate_agent.queue import QueueError, UploadQueue

PayloadBuilder = Callable[[AgentConfig], dict]
ClientFactory = Callable[..., AgentClient]
QueueFactory = Callable[[Path, int], UploadQueue]
Sleeper = Callable[[float], None]


def flush_upload_queue(
    queue: UploadQueue,
    client: AgentClient,
    output: TextIO,
    error_output: TextIO,
) -> tuple[int, int]:
    """Retry oldest-first, deleting entries only after confirmed success."""
    uploaded = failed = 0
    for path in queue.entries():
        try:
            endpoint, payload = queue.read(path)
        except QueueError as error:
            print(f"Skipped a queue entry: {error}", file=error_output)
            failed += 1
            continue
        try:
            client.post(endpoint, payload)
        except AgentClientError as error:
            print(str(error), file=error_output)
            failed += 1
            if error.retryable:
                break
            continue
        queue.delete(path)
        uploaded += 1
    if uploaded:
        print(f"Flushed {uploaded} queued upload(s).", file=output)
    return uploaded, failed


def _post_or_queue(
    client: AgentClient,
    queue: UploadQueue,
    endpoint: str,
    payload: dict,
    output: TextIO,
    error_output: TextIO,
) -> bool:
    try:
        client.post(endpoint, payload)
        return True
    except AgentClientError as error:
        print(str(error), file=error_output)
        if error.retryable:
            try:
                queue.enqueue(endpoint, payload)
                label = endpoint.rsplit("/", 1)[-1]
                print(f"Server unavailable; queued {label} upload.", file=output)
            except QueueError as queue_error:
                print(str(queue_error), file=error_output)
        return False


def _require_token(config: AgentConfig, error_output: TextIO) -> bool:
    if config.device_token:
        return True
    print(
        "FIXMATE_DEVICE_TOKEN is required unless --dry-run is used.",
        file=error_output,
    )
    return False


def run_once(
    config: AgentConfig,
    output: TextIO,
    error_output: TextIO,
    payload_builder: PayloadBuilder = build_scan_payload,
    client_factory: ClientFactory = AgentClient,
    queue_factory: QueueFactory = UploadQueue,
) -> int:
    """Collect once, preserving dry-run while queueing retryable failures."""
    scan = payload_builder(config)
    if config.dry_run:
        print(json.dumps(scan, indent=2, sort_keys=True), file=output)
        return 0
    if not _require_token(config, error_output):
        return 2
    client = client_factory(config.server_url, config.device_token, config.timeout_seconds)
    queue = queue_factory(config.queue_dir, config.max_queue_files)
    flush_upload_queue(queue, client, output, error_output)
    requests = (
        ("/api/v1/agent/register", registration_payload(config, scan)),
        ("/api/v1/agent/heartbeat", heartbeat_payload(config, scan)),
        ("/api/v1/agent/scans", scan),
    )
    successful = [
        _post_or_queue(client, queue, endpoint, payload, output, error_output)
        for endpoint, payload in requests
    ]
    if all(successful):
        print(f"Uploaded one diagnostic batch for {config.device_name}.", file=output)
        return 0
    return 1


def _refresh_registration(
    config: AgentConfig,
    client: AgentClient,
    queue: UploadQueue,
    output: TextIO,
    error_output: TextIO,
) -> bool:
    """Register or refresh a device without collecting full diagnostics."""
    return _post_or_queue(
        client,
        queue,
        "/api/v1/agent/register",
        minimal_registration_payload(config),
        output,
        error_output,
    )


def _run_scheduled_cycle(
    config: AgentConfig,
    client: AgentClient,
    queue: UploadQueue,
    output: TextIO,
    error_output: TextIO,
    payload_builder: PayloadBuilder,
    iteration: int,
) -> bool:
    """Run one scheduled cycle, returning whether all attempted uploads succeeded."""
    print(f"Cycle {iteration}: sending heartbeat.", file=output)
    heartbeat_ok = _post_or_queue(
        client,
        queue,
        "/api/v1/agent/heartbeat",
        current_heartbeat_payload(config),
        output,
        error_output,
    )
    flush_upload_queue(queue, client, output, error_output)
    if config.heartbeat_only:
        print(f"Cycle {iteration}: heartbeat-only mode; skipped scan upload.", file=output)
        return heartbeat_ok
    print(f"Cycle {iteration}: collecting diagnostics.", file=output)
    scan = payload_builder(config)
    scan_ok = _post_or_queue(
        client,
        queue,
        "/api/v1/agent/scans",
        scan,
        output,
        error_output,
    )
    if scan_ok:
        print(f"Cycle {iteration}: uploaded diagnostic scan.", file=output)
    return heartbeat_ok and scan_ok


def run_scheduled(
    config: AgentConfig,
    output: TextIO,
    error_output: TextIO,
    payload_builder: PayloadBuilder = build_scan_payload,
    client_factory: ClientFactory = AgentClient,
    queue_factory: QueueFactory = UploadQueue,
    sleeper: Sleeper = time.sleep,
) -> int:
    """Run bounded or continuous scheduled cycles until stopped."""
    if not _require_token(config, error_output):
        return 2
    client = client_factory(config.server_url, config.device_token, config.timeout_seconds)
    queue = queue_factory(config.queue_dir, config.max_queue_files)
    _refresh_registration(config, client, queue, output, error_output)
    interval_seconds = config.interval_seconds
    total_iterations = config.max_iterations or (1 if interval_seconds is None else None)
    iteration = 0
    had_failure = False
    print(
        "Starting scheduled endpoint agent"
        + (" in heartbeat-only mode." if config.heartbeat_only else "."),
        file=output,
    )
    try:
        while total_iterations is None or iteration < total_iterations:
            iteration += 1
            if not _run_scheduled_cycle(
                config, client, queue, output, error_output, payload_builder, iteration
            ):
                had_failure = True
            if total_iterations is not None and iteration >= total_iterations:
                break
            if interval_seconds is None:
                break
            print(f"Sleeping {interval_seconds:g} second(s) before next cycle.", file=output)
            sleeper(interval_seconds)
    except KeyboardInterrupt:
        print("Scheduled endpoint agent stopped by Ctrl+C.", file=output)
        return 130
    print(f"Completed {iteration} scheduled cycle(s).", file=output)
    return 1 if had_failure else 0


def run_queue_command(
    config: AgentConfig,
    output: TextIO,
    error_output: TextIO,
    client_factory: ClientFactory = AgentClient,
    queue_factory: QueueFactory = UploadQueue,
) -> int:
    """Inspect or explicitly flush the local queue without collecting metrics."""
    queue = queue_factory(config.queue_dir, config.max_queue_files)
    if config.queue_status:
        status = queue.status()
        print(
            f"Queue: {status.queued} valid, {status.corrupted} corrupted, "
            f"{status.total_bytes} bytes.",
            file=output,
        )
        return 0
    if not config.device_token:
        print("FIXMATE_DEVICE_TOKEN is required to flush the queue.", file=error_output)
        return 2
    client = client_factory(config.server_url, config.device_token, config.timeout_seconds)
    _, failed = flush_upload_queue(queue, client, output, error_output)
    return 1 if failed else 0


def run_agent(config: AgentConfig, output: TextIO, error_output: TextIO) -> int:
    """Route queue, scheduled, and default one-shot behavior."""
    if config.queue_status or config.flush_queue:
        return run_queue_command(config, output, error_output)
    if config.interval_seconds is not None or config.heartbeat_only or config.max_iterations:
        return run_scheduled(config, output, error_output)
    return run_once(config, output, error_output)
