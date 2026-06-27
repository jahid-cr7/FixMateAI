"""Pydantic contracts for fleet devices and endpoint-agent submissions."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

DEVICE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")


def validate_device_id_value(value: str) -> str:
    """Accept only opaque identifiers that are safe in URLs and logs."""
    if not DEVICE_ID_PATTERN.fullmatch(value):
        raise ValueError("device_id contains unsupported characters")
    return value


class DeviceRegistrationRequest(BaseModel):
    device_id: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=1, max_length=100)
    operating_system: str = Field(min_length=1, max_length=100)
    platform: str = Field(min_length=1, max_length=100)
    agent_version: str = Field(min_length=1, max_length=32)
    timestamp: datetime

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, value: str) -> str:
        return validate_device_id_value(value)


class DeviceHeartbeatRequest(BaseModel):
    device_id: str = Field(min_length=3, max_length=64)
    timestamp: datetime
    status: str = Field(default="online", pattern=r"^(online|degraded)$")
    agent_version: str = Field(min_length=1, max_length=32)

    _validate_device_id = field_validator("device_id")(validate_device_id_value)


class AgentSystemSummary(BaseModel):
    operating_system: str = Field(min_length=1, max_length=100)
    platform: str = Field(min_length=1, max_length=100)
    cpu_percent: float | None = Field(default=None, ge=0, le=100)
    memory_percent: float | None = Field(default=None, ge=0, le=100)
    disk_used_percent: float | None = Field(default=None, ge=0, le=100)
    disk_free_percent: float | None = Field(default=None, ge=0, le=100)
    boot_time: datetime | None = None


class AgentNetworkSummary(BaseModel):
    connection_status: bool
    internet_connected: bool
    timed_out: bool
    latency_ms: float | None = Field(default=None, ge=0)
    bytes_sent: int | None = Field(default=None, ge=0)
    bytes_received: int | None = Field(default=None, ge=0)
    active_interface_count: int = Field(ge=0, le=100)


class AgentIssue(BaseModel):
    source: str = Field(pattern=r"^(system|network)$")
    code: str = Field(min_length=1, max_length=64)
    severity: str = Field(pattern=r"^(low|medium|high|critical)$")
    evidence: str = Field(min_length=1, max_length=1000)
    explanation: str = Field(min_length=1, max_length=2000)
    recommendation: str = Field(min_length=1, max_length=2000)


class DeviceScanUploadRequest(BaseModel):
    device_id: str = Field(min_length=3, max_length=64)
    timestamp: datetime
    agent_version: str = Field(min_length=1, max_length=32)
    health_score: int = Field(ge=0, le=100)
    system: AgentSystemSummary
    network: AgentNetworkSummary
    issues: list[AgentIssue] = Field(default_factory=list, max_length=100)

    _validate_device_id = field_validator("device_id")(validate_device_id_value)


class DeviceSummary(BaseModel):
    device_id: str
    display_name: str
    operating_system: str
    platform: str
    agent_version: str
    first_seen_at: datetime
    last_seen_at: datetime
    status: str
    notes: str
    latest_health_score: int | None = None
    highest_severity: str | None = None
    issue_count: int = 0
    high_risk: bool = False


class DeviceRegistrationResult(BaseModel):
    device: DeviceSummary
    message: str


class DeviceHeartbeatResult(BaseModel):
    device_id: str
    timestamp: datetime
    status: str
    agent_version: str


class DeviceScanBatch(BaseModel):
    id: int
    device_id: str
    timestamp: datetime
    payload_summary: dict[str, Any]
    health_score: int
    highest_severity: str | None = None
    issue_count: int


class FleetIssueRecord(BaseModel):
    id: int
    device_id: str
    batch_id: int
    source: str
    code: str
    severity: str
    evidence: str
    explanation: str
    recommendation: str
    status: str
    technician_note: str
    detected_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    updated_at: datetime | None = None


class FleetIssueUpdateRequest(BaseModel):
    technician_note: str = Field(default="", max_length=2000)
