"""Fleet orchestration reused by API routes and the Streamlit dashboard."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.schemas.devices import (
    DeviceHeartbeatRequest,
    DeviceRegistrationRequest,
    DeviceScanUploadRequest,
)
from src.fleet import FleetStore
from src.fleet_status import filter_devices


class DeviceService:
    """Small service boundary over privacy-safe fleet persistence."""

    def __init__(
        self,
        database_path: Path,
        online_minutes: int = 5,
        database_url: str | None = None,
    ) -> None:
        self.store = FleetStore(database_path, database_url)
        self.online_minutes = online_minutes

    def register(
        self, payload: DeviceRegistrationRequest, token: str
    ) -> dict[str, Any]:
        data = payload.model_dump(mode="json")
        data["timestamp"] = payload.timestamp.astimezone(timezone.utc).isoformat()
        return self.store.register_device(data, token)

    def authenticate(self, device_id: str, token: str | None) -> bool:
        return bool(token) and self.store.token_matches_device(device_id, token or "")

    def heartbeat(self, payload: DeviceHeartbeatRequest) -> dict[str, Any]:
        data = payload.model_dump(mode="json")
        data["timestamp"] = payload.timestamp.astimezone(timezone.utc).isoformat()
        return self.store.record_heartbeat(data)

    def upload_scan(self, payload: DeviceScanUploadRequest) -> dict[str, Any]:
        data = payload.model_dump(mode="json")
        data["timestamp"] = payload.timestamp.astimezone(timezone.utc).isoformat()
        return self.store.record_scan_batch(data)

    def list_devices(
        self,
        operating_system: str | None = None,
        status: str | None = None,
        severity: str | None = None,
    ) -> list[dict[str, Any]]:
        devices = self.store.list_devices(
            self.online_minutes, now=datetime.now(timezone.utc)
        )
        return filter_devices(devices, operating_system, status, severity)

    def get_device(self, device_id: str) -> dict[str, Any] | None:
        return self.store.get_device(device_id, self.online_minutes)

    def latest(self, device_id: str) -> dict[str, Any] | None:
        return self.store.latest_scan(device_id)

    def history(self, device_id: str, page: int, page_size: int) -> dict[str, Any]:
        return self.store.scan_history(device_id, page, page_size)

    def list_fleet_issues(
        self,
        device_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.store.list_fleet_issues(device_id, status)

    def update_fleet_issue(
        self,
        issue_id: int,
        status: str,
        technician_note: str = "",
    ) -> dict[str, Any] | None:
        return self.store.update_fleet_issue(issue_id, status, technician_note)
