"""Deterministic matching of OCR text to curated troubleshooting entries."""

from __future__ import annotations

import re
import unicodedata
from typing import TypedDict

from src.knowledge_base import KnowledgeEntry

MIN_RELIABLE_CONFIDENCE = 60.0
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*")


class ErrorMatch(TypedDict):
    """A ranked knowledge-base result and the evidence behind its score."""

    issue: KnowledgeEntry
    confidence: float
    evidence: list[str]
    reliable: bool


def normalize_text(text: str) -> str:
    """Normalize OCR text for deterministic, case-insensitive matching."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = re.sub(r"[^a-z0-9._:/\\\s-]", " ", normalized)
    return " ".join(normalized.split())


def _tokens(text: str) -> set[str]:
    """Extract stable alphanumeric tokens from normalized text."""
    return set(TOKEN_PATTERN.findall(text))


def _score_entry(normalized_text: str, entry: KnowledgeEntry) -> tuple[float, list[str]]:
    """Score exact phrases first, then meaningful multi-token partial matches."""
    text_tokens = _tokens(normalized_text)
    exact_hits: list[str] = []
    partial_hits: list[str] = []
    best_partial = 0.0

    for pattern in entry["patterns"]:
        normalized_pattern = normalize_text(pattern)
        if not normalized_pattern:
            continue
        if normalized_pattern in normalized_text:
            exact_hits.append(pattern)
            continue

        pattern_tokens = _tokens(normalized_pattern)
        shared = pattern_tokens & text_tokens
        if len(pattern_tokens) >= 2 and shared:
            coverage = len(shared) / len(pattern_tokens)
            if coverage >= 0.5:
                best_partial = max(best_partial, coverage)
                partial_hits.append(
                    f"{pattern} (matched words: {', '.join(sorted(shared))})"
                )

    if exact_hits:
        specificity = max(len(_tokens(normalize_text(hit))) for hit in exact_hits)
        score = min(99.0, 72.0 + min(18.0, specificity * 4.0) + (len(exact_hits) - 1) * 3.0)
        return score, [f'Exact phrase: "{hit}"' for hit in exact_hits]
    if partial_hits:
        score = min(79.0, 35.0 + best_partial * 40.0)
        return score, [f"Partial phrase: {hit}" for hit in partial_hits]
    return 0.0, []


def rank_error_matches(
    text: str,
    entries: list[KnowledgeEntry],
    minimum_confidence: float = MIN_RELIABLE_CONFIDENCE,
) -> list[ErrorMatch]:
    """Return deterministic results sorted by confidence then stable issue ID."""
    normalized = normalize_text(text)
    if not normalized:
        return []

    matches: list[ErrorMatch] = []
    for entry in entries:
        confidence, evidence = _score_entry(normalized, entry)
        if confidence <= 0:
            continue
        matches.append(
            {
                "issue": entry,
                "confidence": round(confidence, 1),
                "evidence": evidence,
                "reliable": confidence >= minimum_confidence,
            }
        )
    return sorted(matches, key=lambda match: (-match["confidence"], match["issue"]["id"]))


def reliable_matches(matches: list[ErrorMatch]) -> list[ErrorMatch]:
    """Return only results that meet the declared confidence floor."""
    return [match for match in matches if match["reliable"]]
