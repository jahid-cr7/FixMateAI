"""API adapter for deterministic and optional hybrid assistant modes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.hybrid_agent import run_hybrid_assistant
from src.llm import create_provider
from src.troubleshooting_assistant import answer_question


class AssistantService:
    """Keep assistant orchestration outside HTTP route handlers."""

    def __init__(
        self,
        database_path: Path,
        database_url: str | None = None,
    ) -> None:
        self.database_path = database_path
        self.database_url = database_url

    def query(
        self,
        question: str,
        ai_enhanced: bool,
        external_consent: bool,
    ) -> dict[str, Any]:
        """Return deterministic truth plus optional bounded explanation metadata."""
        if not ai_enhanced:
            answer = answer_question(
                question,
                database_path=self.database_path,
                database_url=self.database_url,
            )
            return {
                **answer,
                "ai_generated": False,
                "ai_explanation": None,
                "provider_name": None,
                "fallback_used": False,
                "fallback_reason": None,
            }
        hybrid = run_hybrid_assistant(
            question,
            create_provider(),
            consent_external=external_consent,
            database_path=self.database_path,
            database_url=self.database_url,
        )
        return {
            **hybrid["answer"],
            "ai_generated": hybrid["ai_generated"],
            "ai_explanation": hybrid["ai_explanation"],
            "provider_name": hybrid["provider_name"],
            "fallback_used": hybrid["fallback_used"],
            "fallback_reason": hybrid["fallback_reason"],
        }
