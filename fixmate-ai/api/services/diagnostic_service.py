"""Service orchestration that reuses existing collectors, detectors, and storage."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.collector import collect_system_metrics
from src.database import save_network_diagnostic, save_scan
from src.detector import detect_issues
from src.health_score import calculate_health_score
from src.network_collector import collect_network_diagnostic
from src.network_detector import detect_network_issues

from api.services.data_service import DataService
from api.services.errors import ServiceUnavailableError


class DiagnosticService:
    """Run existing read-only diagnostics and persist results atomically."""

    def __init__(
        self,
        database_path: Path,
        data_service: DataService,
        database_url: str | None = None,
    ) -> None:
        self.database_path = database_path
        self.data_service = data_service
        self.database_url = database_url

    def run_system_scan(self) -> dict[str, Any]:
        """Collect, detect, score, save, and return a system scan."""
        try:
            scan = collect_system_metrics()
            issues = detect_issues(
                scan.get("cpu_percent"),
                scan.get("memory_percent"),
                scan.get("disk_free_percent"),
            )
            score = calculate_health_score(issues)
            save_scan(scan, issues, score, self.database_path, self.database_url)
            result = self.data_service.latest_system()
        except Exception as error:
            raise ServiceUnavailableError("System metric collection failed.") from error
        if result is None:
            raise ServiceUnavailableError("System scan could not be retrieved after saving.")
        return result

    def run_network_diagnostic(
        self,
        host: str,
        port: int,
        timeout_seconds: float,
        latency_threshold_ms: float,
    ) -> dict[str, Any]:
        """Collect, detect, save, and return a network diagnostic."""
        try:
            diagnostic = collect_network_diagnostic(
                host=host,
                port=port,
                timeout_seconds=timeout_seconds,
                latency_threshold_ms=latency_threshold_ms,
            )
            issues = detect_network_issues(diagnostic)
            save_network_diagnostic(diagnostic, issues, self.database_path, self.database_url)
            result = self.data_service.latest_network()
        except Exception as error:
            raise ServiceUnavailableError("Network diagnostic failed.") from error
        if result is None:
            raise ServiceUnavailableError(
                "Network diagnostic could not be retrieved after saving."
            )
        return result
