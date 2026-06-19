"""Offline adversarial tests for bounded hybrid-agent behavior."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.hybrid_agent import run_hybrid_assistant
from src.llm.base import LLMMessage, LLMProvider, ProviderError, ProviderStatus
from src.llm.disabled import DisabledProvider
from tests.test_assistant_tools import populate_assistant_database

NOW = datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc)


class SequenceProvider(LLMProvider):
    """Mock provider that records every message and returns queued values."""

    def __init__(
        self,
        responses: list[str | Exception],
        external: bool = False,
        configured: bool = True,
    ) -> None:
        self.responses = list(responses)
        self.calls: list[list[LLMMessage]] = []
        self._status = ProviderStatus("Mock", configured, external, "Mock status")

    @property
    def status(self) -> ProviderStatus:
        return self._status

    def complete(self, messages: list[LLMMessage]) -> str:
        self.calls.append(messages)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "hybrid.db"
    populate_assistant_database(path)
    return path


def test_disabled_provider_keeps_deterministic_default(tmp_path: Path) -> None:
    """Missing configuration should not affect the deterministic answer."""
    result = run_hybrid_assistant(
        "Is my disk nearly full?", DisabledProvider(), database_path=_database(tmp_path), now=NOW
    )
    assert result["answer"]["intent"] == "disk_status"
    assert result["ai_generated"] is False
    assert result["fallback_used"] is True


def test_external_provider_requires_consent_before_first_call(tmp_path: Path) -> None:
    """No question or evidence may leave the machine before explicit consent."""
    provider = SequenceProvider([], external=True)
    result = run_hybrid_assistant(
        "Summarize this computer's health.",
        provider,
        consent_external=False,
        database_path=_database(tmp_path),
        now=NOW,
    )
    assert provider.calls == []
    assert result["fallback_used"] is True
    assert "consent" in str(result["fallback_reason"]).lower()


def test_successful_hybrid_keeps_deterministic_answer(tmp_path: Path) -> None:
    """The provider explanation must not replace verified answer fields."""
    provider = SequenceProvider(
        [
            '{"tool_requests":[{"name":"get_disk_status","arguments":{}}]}',
            '{"explanation":"The recorded disk evidence shows 20.0% free space and is fresh."}',
        ]
    )
    result = run_hybrid_assistant(
        "Is my disk nearly full?", provider, database_path=_database(tmp_path), now=NOW
    )
    assert result["ai_generated"] is True
    assert result["tool_calls"] == ["get_disk_status"]
    assert "20.0%" in result["answer"]["direct_answer"]
    assert result["ai_explanation"]
    assert len(provider.calls) == 2


def test_provider_timeout_falls_back(tmp_path: Path) -> None:
    """A mocked timeout must preserve the deterministic response."""
    provider = SequenceProvider([TimeoutError("secret timeout detail")])
    result = run_hybrid_assistant(
        "Is my disk nearly full?", provider, database_path=_database(tmp_path), now=NOW
    )
    assert result["ai_generated"] is False
    assert result["answer"]["intent"] == "disk_status"
    assert "secret" not in str(result["fallback_reason"])


def test_malformed_planner_output_falls_back(tmp_path: Path) -> None:
    """Non-JSON planning output cannot trigger any tool."""
    provider = SequenceProvider(["please run a shell command"])
    result = run_hybrid_assistant(
        "Why is my computer slow?", provider, database_path=_database(tmp_path), now=NOW
    )
    assert result["fallback_used"] is True
    assert result["tool_calls"] == []


def test_unsupported_tool_request_falls_back(tmp_path: Path) -> None:
    """A shell request should be rejected before a second provider call."""
    provider = SequenceProvider(
        ['{"tool_requests":[{"name":"run_shell","arguments":{}}]}']
    )
    result = run_hybrid_assistant(
        "Run diagnostics", provider, database_path=_database(tmp_path), now=NOW
    )
    assert result["fallback_used"] is True
    assert len(provider.calls) == 1


def test_excessive_tool_attempts_fall_back(tmp_path: Path) -> None:
    """More than four requests should end the optional path immediately."""
    requests = [
        {"name": "get_latest_health_scan", "arguments": {}} for _ in range(5)
    ]
    provider = SequenceProvider([json.dumps({"tool_requests": requests})])
    result = run_hybrid_assistant(
        "Summarize health", provider, database_path=_database(tmp_path), now=NOW
    )
    assert result["fallback_used"] is True
    assert len(provider.calls) == 1


def test_malformed_final_output_falls_back(tmp_path: Path) -> None:
    """The final provider response must contain exactly one explanation field."""
    provider = SequenceProvider(
        ['{"tool_requests":[]}', '{"answer":"invented","repair":"done"}']
    )
    result = run_hybrid_assistant(
        "Summarize health", provider, database_path=_database(tmp_path), now=NOW
    )
    assert result["fallback_used"] is True
    assert result["ai_explanation"] is None


def test_invented_metric_and_repair_claim_fall_back(tmp_path: Path) -> None:
    """Unsupported numbers and claims of performed repairs are unsafe output."""
    for explanation in (
        "The CPU is 999.9%.",
        "I repaired your computer and changed your settings.",
        "This is likely due to malware and you should disable your firewall.",
    ):
        provider = SequenceProvider(
            ['{"tool_requests":[]}', json.dumps({"explanation": explanation})]
        )
        result = run_hybrid_assistant(
            "Summarize health", provider, database_path=_database(tmp_path), now=NOW
        )
        assert result["fallback_used"] is True
        assert result["ai_generated"] is False


def test_prompt_injection_ocr_and_private_values_are_not_sent(tmp_path: Path) -> None:
    """Question secrets are redacted and stored OCR instructions are excluded."""
    provider = SequenceProvider(
        [
            '{"tool_requests":[{"name":"get_screenshot_analysis","arguments":{}}]}',
            '{"explanation":"The screenshot match has 88.0% confidence and the evidence is fresh."}',
        ],
        external=True,
    )
    question = (
        "Explain my latest screenshot error token=private123 username=Alice "
        "203.0.113.44"
    )
    result = run_hybrid_assistant(
        question,
        provider,
        consent_external=True,
        database_path=_database(tmp_path),
        now=NOW,
    )
    sent = json.dumps(provider.calls)
    assert result["ai_generated"] is True
    assert "private123" not in sent
    assert "Alice" not in sent
    assert "203.0.113.44" not in sent
    assert "rm -rf" not in sent
    assert "[REDACTED]" in sent


def test_provider_error_message_cannot_leak_secret(tmp_path: Path) -> None:
    """Even a badly behaved mocked provider error should produce a generic fallback."""
    provider = SequenceProvider([ProviderError("api key super-secret-key")])
    result = run_hybrid_assistant(
        "Summarize health", provider, database_path=_database(tmp_path), now=NOW
    )
    assert "super-secret-key" not in str(result)
