"""Command-line entry point for the endpoint agent."""

from __future__ import annotations

import sys

from fixmate_agent.config import parse_agent_config
from fixmate_agent.runner import run_agent


def main(argv: list[str] | None = None) -> int:
    """Parse settings and dispatch the selected safe agent mode."""
    config = parse_agent_config(argv)
    return run_agent(config, sys.stdout, sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
