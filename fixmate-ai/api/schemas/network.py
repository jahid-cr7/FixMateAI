"""Network diagnostic request and response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NetworkIssueSummary(BaseModel):
    """Issue attached to a network diagnostic."""

    id: str
    code: str
    severity: str
    evidence: str
    explanation: str
    recommendation: str
    detected_at: datetime


class NetworkDiagnosticRequest(BaseModel):
    """Bounded configuration for one safe connectivity check."""

    host: str = Field(default="1.1.1.1", min_length=1, max_length=253)
    port: int = Field(default=443, ge=1, le=65535)
    timeout_seconds: float = Field(default=1.5, ge=0.1, le=5.0)
    latency_threshold_ms: float = Field(default=150.0, ge=1.0, le=5000.0)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "host": "1.1.1.1",
                    "port": 443,
                    "timeout_seconds": 1.5,
                    "latency_threshold_ms": 150.0,
                }
            ]
        }
    )

    @field_validator("host")
    @classmethod
    def clean_host(cls, value: str) -> str:
        """Reject whitespace/control characters and URL-shaped targets."""
        cleaned = value.strip()
        if any(character.isspace() for character in cleaned) or "://" in cleaned:
            raise ValueError("host must be a hostname or IP address without a URL scheme")
        return cleaned


class NetworkDiagnostic(BaseModel):
    """Privacy-safe stored or newly collected network result."""

    id: int
    collected_at: datetime
    connection_status: bool
    internet_connected: bool
    timed_out: bool
    latency_ms: float | None = None
    latency_threshold_ms: float
    active_interface_count: int = Field(ge=0)
    bytes_sent: int | None = Field(default=None, ge=0)
    bytes_received: int | None = Field(default=None, ge=0)
    issues: list[NetworkIssueSummary] = Field(default_factory=list)


class NetworkHistoryItem(BaseModel):
    """Compact historical network record."""

    id: int
    collected_at: datetime
    connection_status: bool
    internet_connected: bool
    timed_out: bool
    latency_ms: float | None = None
    bytes_sent: int | None = None
    bytes_received: int | None = None
