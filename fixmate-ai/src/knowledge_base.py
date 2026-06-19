"""Loading and validation for the local troubleshooting knowledge base."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast

DEFAULT_KNOWLEDGE_BASE_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "error_knowledge_base.json"
)


class KnowledgeEntry(TypedDict):
    """One curated Windows or Ubuntu troubleshooting entry."""

    id: str
    patterns: list[str]
    operating_system: str
    title: str
    likely_causes: list[str]
    troubleshooting_steps: list[str]
    severity: str
    documentation_notes: str


REQUIRED_FIELDS = {
    "id",
    "patterns",
    "operating_system",
    "title",
    "likely_causes",
    "troubleshooting_steps",
    "severity",
    "documentation_notes",
}


def load_knowledge_base(
    path: Path = DEFAULT_KNOWLEDGE_BASE_PATH,
) -> list[KnowledgeEntry]:
    """Load and minimally validate the trusted local JSON knowledge base."""
    with path.open("r", encoding="utf-8") as source:
        raw_entries = json.load(source)
    if not isinstance(raw_entries, list):
        raise ValueError("Knowledge base root must be a JSON list.")

    entries: list[KnowledgeEntry] = []
    seen_ids: set[str] = set()
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict) or not REQUIRED_FIELDS <= raw_entry.keys():
            raise ValueError("A knowledge-base entry is missing required fields.")
        entry = cast(KnowledgeEntry, raw_entry)
        if not entry["id"] or entry["id"] in seen_ids:
            raise ValueError("Knowledge-base IDs must be non-empty and unique.")
        if not entry["patterns"]:
            raise ValueError(f"Knowledge-base entry {entry['id']} needs a pattern.")
        seen_ids.add(entry["id"])
        entries.append(entry)
    return entries

