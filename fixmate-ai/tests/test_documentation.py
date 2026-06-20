"""Lightweight portfolio documentation and synthetic asset validation."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
README = PROJECT_ROOT / "README.md"
ASSETS = (
    "docs/assets/system-health.svg",
    "docs/assets/screenshot-analyzer.svg",
    "docs/assets/assistant.svg",
    "docs/assets/reports.svg",
    "docs/assets/swagger.svg",
)


def test_readme_local_links_exist() -> None:
    """Every relative Markdown link in the portfolio README should resolve."""
    content = README.read_text(encoding="utf-8")
    targets = re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", content)
    missing: list[str] = []
    for target in targets:
        clean = target.strip().split("#", 1)[0]
        if not clean or clean.startswith(("http://", "https://", "mailto:")):
            continue
        if not (PROJECT_ROOT / clean).exists():
            missing.append(target)
    assert missing == []


def test_required_portfolio_documents_and_assets_exist() -> None:
    required = {
        "docs/ARCHITECTURE.md",
        "docs/DEMO.md",
        "docs/INTERVIEW_GUIDE.md",
        "docs/PRIVACY.md",
        "docs/ROADMAP.md",
        "docs/SECURITY.md",
        "docs/PHASE9_PLAN.md",
        "scripts/generate_demo_data.py",
        *ASSETS,
    }
    assert all((PROJECT_ROOT / path).is_file() for path in required)


def test_visual_assets_are_explicitly_synthetic_and_private() -> None:
    forbidden = (
        "c:\\users\\",
        "/home/",
        "@gmail.",
        "@outlook.",
        "192.168.",
        "10.0.0.",
        "api_key",
        "password=",
    )
    for relative_path in ASSETS:
        asset_path = PROJECT_ROOT / relative_path
        content = asset_path.read_text(encoding="utf-8")
        assert "SYNTHETIC DEMO" in content
        assert "<svg" in content
        assert all(value not in content.casefold() for value in forbidden)
        root = ET.parse(asset_path).getroot()
        assert root.tag.endswith("svg")
        assert root.attrib["viewBox"] == "0 0 1200 675"


def test_readme_does_not_claim_autonomous_repair() -> None:
    content = README.read_text(encoding="utf-8").casefold()
    assert "does not perform or claim autonomous repair" in content
    assert "python scripts/generate_demo_data.py" in content
    assert "python -m pytest -v" in content
