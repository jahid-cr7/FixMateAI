"""Tests for deterministic exact, partial, weak, and absent matching."""

from src.error_matcher import rank_error_matches, reliable_matches
from src.knowledge_base import load_knowledge_base


def test_exact_match_is_high_confidence() -> None:
    """A distinctive exact phrase should produce a reliable top result."""
    matches = rank_error_matches(
        "ModuleNotFoundError: No module named 'requests'",
        load_knowledge_base(),
    )
    assert matches[0]["issue"]["id"] == "python_module_not_found"
    assert matches[0]["confidence"] >= 70
    assert matches[0]["reliable"] is True
    assert "Exact phrase" in matches[0]["evidence"][0]


def test_partial_match_can_be_reliable() -> None:
    """Meaningful OCR word overlap should survive a missing word."""
    matches = rank_error_matches(
        "The certificate verify step reported a problem",
        load_knowledge_base(),
    )
    ssl_match = next(
        match for match in matches if match["issue"]["id"] == "ssl_certificate_error"
    )
    assert ssl_match["reliable"] is True
    assert "Partial phrase" in ssl_match["evidence"][0]


def test_weak_match_is_not_reliable() -> None:
    """Sparse overlap may be ranked but must not be shown as a solution."""
    matches = rank_error_matches(
        "The certificate was trusted yesterday",
        load_knowledge_base(),
    )
    ssl_match = next(
        match for match in matches if match["issue"]["id"] == "ssl_certificate_error"
    )
    assert ssl_match["confidence"] < 60
    assert ssl_match["reliable"] is False
    assert ssl_match not in reliable_matches(matches)


def test_missing_match_returns_no_result() -> None:
    """Unrelated text should not generate invented troubleshooting advice."""
    matches = rank_error_matches(
        "A purple bicycle crossed the quiet garden",
        load_knowledge_base(),
    )
    assert matches == []
    assert reliable_matches(matches) == []


def test_knowledge_base_contains_required_entries() -> None:
    """The local data file must contain at least the approved 15 issues."""
    entries = load_knowledge_base()
    assert len(entries) >= 15
    assert len({entry["id"] for entry in entries}) == len(entries)

