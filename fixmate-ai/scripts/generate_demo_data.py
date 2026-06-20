"""Generate a deterministic, clearly synthetic FixMate AI demonstration database."""

from __future__ import annotations

import argparse
import random
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import (  # noqa: E402
    DEFAULT_DB_PATH,
    connect,
    initialize_database,
    save_network_diagnostic,
    save_scan,
    save_screenshot_analysis,
)
from src.detector import detect_issues  # noqa: E402
from src.health_score import calculate_health_score  # noqa: E402
from src.network_detector import detect_network_issues  # noqa: E402

DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "demo_fixmate.db"
DEMO_MARKER = "fixmate_synthetic_demo_v1"
DEMO_ANCHOR = datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)
ALLOWED_SUFFIXES = {".db", ".sqlite", ".sqlite3"}


class DemoDataSafetyError(RuntimeError):
    """Raised when generation could overwrite or target an unsafe database."""


@dataclass(frozen=True)
class DemoSummary:
    """Counts produced by one deterministic demo generation run."""

    output: Path
    seed: int
    days: int
    system_scans: int
    network_diagnostics: int
    screenshot_analyses: int


def is_demo_database(database_path: Path) -> bool:
    """Return whether a SQLite file carries this generator's synthetic marker."""
    if not database_path.is_file():
        return False
    try:
        with closing(sqlite3.connect(database_path)) as connection:
            row = connection.execute(
                "SELECT marker FROM demo_metadata WHERE marker = ?",
                (DEMO_MARKER,),
            ).fetchone()
    except sqlite3.Error:
        return False
    return row is not None


def _prepare_output(database_path: Path, reset_demo: bool) -> Path:
    """Validate output and remove only a recognized demo when explicitly requested."""
    output = database_path.expanduser().resolve()
    if output == DEFAULT_DB_PATH.resolve():
        raise DemoDataSafetyError(
            "Refusing to use the normal FixMate AI database; choose a demo filename."
        )
    if output.suffix.casefold() not in ALLOWED_SUFFIXES:
        raise DemoDataSafetyError("Demo output must use .db, .sqlite, or .sqlite3.")
    if output.exists():
        if not reset_demo:
            raise DemoDataSafetyError(
                "Output already exists. Use --reset-demo only for a generated demo database."
            )
        if not is_demo_database(output):
            raise DemoDataSafetyError(
                "Refusing to replace an existing database without the synthetic demo marker."
            )
        _reset_demo_database(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def _reset_demo_database(database_path: Path) -> None:
    """Transactionally clear only known tables in a verified synthetic database."""
    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            DELETE FROM issues;
            DELETE FROM scans;
            DELETE FROM network_issues;
            DELETE FROM network_diagnostics;
            DELETE FROM screenshot_analyses;
            DROP TABLE demo_metadata;
            DELETE FROM sqlite_sequence
            WHERE name IN (
                'scans', 'issues', 'network_diagnostics',
                'network_issues', 'screenshot_analyses'
            );
            """
        )
        connection.commit()


def _mark_synthetic(database_path: Path, seed: int, days: int) -> None:
    """Add metadata that clearly identifies this database as generated demo data."""
    with connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE demo_metadata (
                marker TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                seed INTEGER NOT NULL,
                days INTEGER NOT NULL,
                anchor_timestamp TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO demo_metadata
                (marker, label, seed, days, anchor_timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                DEMO_MARKER,
                "SYNTHETIC DEMO DATA - NOT A REAL DEVICE",
                seed,
                days,
                DEMO_ANCHOR.isoformat(),
            ),
        )


def _system_scan(rng: random.Random, timestamp: datetime, day_index: int) -> dict:
    """Create one realistic synthetic system snapshot without personal identifiers."""
    cpu = 93.5 if day_index % 7 == 3 else round(rng.uniform(24, 76), 1)
    memory = 88.2 if day_index % 9 == 5 else round(rng.uniform(38, 79), 1)
    disk_free = 7.5 if day_index % 11 == 8 else round(max(12, 42 - day_index * 0.8), 1)
    processes = [
        {"pid": 4100 + day_index, "name": "demo-browser", "memory_mb": round(rng.uniform(620, 980), 1)},
        {"pid": 5100 + day_index, "name": "demo-editor", "memory_mb": round(rng.uniform(310, 560), 1)},
        {"pid": 6100 + day_index, "name": "demo-video-call", "memory_mb": round(rng.uniform(180, 420), 1)},
        {"pid": 7100 + day_index, "name": "demo-terminal", "memory_mb": round(rng.uniform(70, 150), 1)},
        {"pid": 8100 + day_index, "name": "demo-sync-client", "memory_mb": round(rng.uniform(45, 120), 1)},
    ]
    processes.sort(key=lambda item: item["memory_mb"], reverse=True)
    return {
        "collected_at": timestamp.isoformat(),
        "os_name": "Windows" if day_index % 2 == 0 else "Ubuntu",
        "os_version": "SYNTHETIC-DEMO",
        "os_release": "Demo 11" if day_index % 2 == 0 else "Demo 24.04",
        "architecture": "x86_64-demo",
        "boot_time": (timestamp - timedelta(hours=6 + day_index % 5)).isoformat(),
        "cpu_percent": cpu,
        "memory_percent": memory,
        "disk_used_percent": round(100 - disk_free, 1),
        "disk_free_percent": disk_free,
        "top_processes": processes,
    }


def _network_diagnostic(rng: random.Random, timestamp: datetime, day_index: int) -> dict:
    """Create a synthetic connectivity record using a reserved invalid hostname."""
    timed_out = day_index % 8 == 6
    high_latency = day_index % 5 == 2
    latency = None if timed_out else round(rng.uniform(22, 68), 2)
    if high_latency and not timed_out:
        latency = round(rng.uniform(180, 260), 2)
    return {
        "collected_at": timestamp.isoformat(),
        "target_host": "connectivity.demo.invalid",
        "target_port": 443,
        "timeout_seconds": 1.5,
        "latency_threshold_ms": 150.0,
        "active_interfaces": ["Synthetic Ethernet Adapter"],
        "connection_status": True,
        "internet_connected": not timed_out,
        "timed_out": timed_out,
        "latency_ms": latency,
        "bytes_sent": 2_000_000 + day_index * 180_000,
        "bytes_received": 8_000_000 + day_index * 760_000,
    }


def generate_demo_database(
    output: Path = DEFAULT_OUTPUT,
    seed: int = 2026,
    days: int = 14,
    reset_demo: bool = False,
) -> DemoSummary:
    """Generate deterministic synthetic records into a dedicated SQLite database."""
    if not 1 <= days <= 365:
        raise ValueError("days must be between 1 and 365")
    database_path = _prepare_output(output, reset_demo)
    rng = random.Random(seed)
    initialize_database(database_path)
    _mark_synthetic(database_path, seed, days)

    screenshot_count = 0
    for day_index in range(days):
        timestamp = DEMO_ANCHOR - timedelta(days=days - day_index - 1)
        scan = _system_scan(rng, timestamp, day_index)
        system_issues = detect_issues(
            scan["cpu_percent"], scan["memory_percent"], scan["disk_free_percent"]
        )
        save_scan(
            scan,
            system_issues,
            calculate_health_score(system_issues),
            database_path,
        )

        network_timestamp = timestamp + timedelta(minutes=15)
        diagnostic = _network_diagnostic(rng, network_timestamp, day_index)
        network_issues = detect_network_issues(
            diagnostic, detected_at=network_timestamp.isoformat()
        )
        save_network_diagnostic(diagnostic, network_issues, database_path)

        if day_index % 4 == 1:
            screenshot_count += 1
            save_screenshot_analysis(
                analyzed_at=(timestamp + timedelta(minutes=30)).isoformat(),
                anonymized_filename=f"synthetic-demo-image-{screenshot_count:03d}.png",
                extracted_text_redacted=(
                    "SYNTHETIC DEMO: permission denied while opening a demo document."
                ),
                matched_issue_id="permission_denied_linux",
                confidence_score=86.0,
                database_path=database_path,
            )

    return DemoSummary(
        output=database_path,
        seed=seed,
        days=days,
        system_scans=days,
        network_diagnostics=days,
        screenshot_analyses=screenshot_count,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate clearly marked synthetic FixMate AI portfolio data."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="Replace the output only if it is already a marked synthetic demo database.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point with concise, safe failure messages."""
    arguments = _parser().parse_args(argv)
    try:
        summary = generate_demo_database(
            output=arguments.output,
            seed=arguments.seed,
            days=arguments.days,
            reset_demo=arguments.reset_demo,
        )
    except (DemoDataSafetyError, ValueError) as error:
        print(f"Demo data was not generated: {error}", file=sys.stderr)
        return 2
    print("Created SYNTHETIC DEMO DATA - NOT A REAL DEVICE")
    print(f"Output: {summary.output}")
    print(
        f"Seed: {summary.seed}; days: {summary.days}; "
        f"system scans: {summary.system_scans}; "
        f"network diagnostics: {summary.network_diagnostics}; "
        f"screenshot analyses: {summary.screenshot_analyses}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
