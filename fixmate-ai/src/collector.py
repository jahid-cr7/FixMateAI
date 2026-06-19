"""Cross-platform, read-only collection of basic system-health metrics."""

from __future__ import annotations

import platform
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil


def _safe_metric(operation: Any) -> Any | None:
    """Run a metric operation and return None when the OS denies or lacks it."""
    try:
        return operation()
    except (OSError, RuntimeError, ValueError, psutil.Error):
        return None


def _system_disk_path() -> Path:
    """Return a suitable existing path on the current operating-system disk."""
    home = Path.home()
    return Path(home.anchor) if home.anchor else Path("/")


def _top_processes(limit: int = 5) -> list[dict[str, Any]]:
    """Return up to ``limit`` processes ordered by resident memory usage."""
    processes: list[dict[str, Any]] = []
    try:
        iterator = psutil.process_iter(["pid", "name", "memory_info"])
        for process in iterator:
            try:
                info = process.info
                memory_info = info.get("memory_info")
                if memory_info is None:
                    continue
                processes.append(
                    {
                        "pid": info.get("pid"),
                        "name": info.get("name") or "Unknown",
                        "memory_mb": round(memory_info.rss / (1024 * 1024), 1),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except (OSError, RuntimeError, psutil.Error):
        return []

    return sorted(processes, key=lambda item: item["memory_mb"], reverse=True)[:limit]


def collect_system_metrics() -> dict[str, Any]:
    """Collect non-sensitive, read-only system metrics without elevated privileges."""
    cpu_percent = _safe_metric(lambda: psutil.cpu_percent(interval=0.5))
    memory = _safe_metric(psutil.virtual_memory)
    disk = _safe_metric(lambda: psutil.disk_usage(str(_system_disk_path())))
    boot_timestamp = _safe_metric(psutil.boot_time)

    return {
        "collected_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "os_name": platform.system() or "Unknown",
        "os_version": platform.version() or "Unknown",
        "os_release": platform.release() or "Unknown",
        "architecture": platform.machine() or "Unknown",
        "boot_time": (
            datetime.fromtimestamp(boot_timestamp).astimezone().isoformat(timespec="seconds")
            if boot_timestamp is not None
            else None
        ),
        "cpu_percent": float(cpu_percent) if cpu_percent is not None else None,
        "memory_percent": float(memory.percent) if memory is not None else None,
        "disk_used_percent": float(disk.percent) if disk is not None else None,
        "disk_free_percent": (
            round((disk.free / disk.total) * 100, 2)
            if disk is not None and disk.total
            else None
        ),
        "top_processes": _top_processes(),
    }

