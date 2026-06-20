"""Troubleshooting assistant API models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AssistantMode(str, Enum):
    """Supported assistant modes."""

    deterministic = "deterministic"
    ai_enhanced = "ai_enhanced"


class AssistantQueryRequest(BaseModel):
    """Bounded untrusted assistant query."""

    question: str = Field(min_length=1, max_length=2000)
    mode: AssistantMode = AssistantMode.deterministic
    external_consent: bool = False

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "question": "Why is my computer slow?",
                    "mode": "deterministic",
                    "external_consent": False,
                }
            ]
        }
    )


class EvidenceRecord(BaseModel):
    """One evidence item from the deterministic source of truth."""

    label: str
    value: str
    source: str


class AssistantQueryResult(BaseModel):
    """Deterministic answer with optional labeled AI explanation metadata."""

    intent: str
    direct_answer: str
    evidence: list[EvidenceRecord]
    relevant_timestamp: datetime | None = None
    severity: str | None = None
    guidance: list[str]
    sufficient_evidence: bool
    freshness: str
    ai_generated: bool = False
    ai_explanation: str | None = None
    provider_name: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
