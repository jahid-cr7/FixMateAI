"""Command-line entry point for the one-shot endpoint agent."""

from __future__ import annotations

import sys

from fixmate_agent.config import parse_agent_config
from fixmate_agent.runner import run_once


def main(argv: list[str] | None = None) -> int:
    """Parse settings, run exactly once, and return a process exit code."""
    config = parse_agent_config(argv)
    return run_once(config, sys.stdout, sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
