"""Deterministic, evidence-bound troubleshooting question routing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypedDict

from src.assistant_tools import (
    generate_health_summary,
    get_disk_status,
    get_health_scan_history,
    get_issue_history,
    get_latest_health_scan,
    get_network_status,
    get_recent_issues,
    get_screenshot_analysis,
    get_top_resource_processes,
    search_knowledge_base,
)
from src.database import DEFAULT_DATABASE_URL, DEFAULT_DB_PATH
from src.knowledge_base import KnowledgeEntry, load_knowledge_base
from src.privacy import redact_sensitive_text

STALE_AFTER = timedelta(hours=24)
SEVERITY_ORDER = {"high": 3, "medium": 2, "low": 1}


class EvidenceItem(TypedDict):
    """One privacy-safe fact used to form an assistant response."""

    label: str
    value: str
    source: str


class AssistantAnswer(TypedDict):
    """Stable response contract shared by all deterministic routes."""

    intent: str
    direct_answer: str
    evidence: list[EvidenceItem]
    relevant_timestamp: str | None
    severity: str | None
    guidance: list[str]
    sufficient_evidence: bool
    freshness: str


def detect_intent(question: str) -> str:
    """Map a natural-language question to a deterministic supported intent."""
    normalized = " ".join(question.casefold().split())
    if any(phrase in normalized for phrase in ("fix first", "should i fix", "priority", "most urgent")):
        return "fix_priority"
    if "screenshot" in normalized or "ocr" in normalized:
        return "screenshot_error"
    if any(phrase in normalized for phrase in ("detected today", "problems today", "issues today")):
        return "issues_today"
    if any(phrase in normalized for phrase in ("most memory", "using memory", "memory process", "using the most ram")):
        return "memory_usage"
    if any(phrase in normalized for phrase in ("disk nearly full", "disk full", "disk space", "storage nearly full", "free space")):
        return "disk_status"
    if any(phrase in normalized for phrase in ("network slow", "internet slow", "high latency", "network latency")):
        return "network_slow"
    if any(phrase in normalized for phrase in ("internet connection working", "internet working", "am i online", "network working", "connection working")):
        return "internet_status"
    if any(phrase in normalized for phrase in ("computer slow", "computer is slow", "why is my pc slow", "system slow", "sluggish", "performance slow")):
        return "computer_slow"
    if any(phrase in normalized for phrase in ("summarize", "health summary", "computer health", "system health")):
        return "health_summary"
    return "unknown"


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse timestamps for deterministic freshness labels."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def data_freshness(
    timestamp: str | None,
    now: datetime | None = None,
) -> str:
    """Classify evidence as fresh, stale, or unavailable."""
    parsed = _parse_timestamp(timestamp)
    if parsed is None:
        return "Unavailable"
    current = now or datetime.now().astimezone()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    age = current.astimezone(timezone.utc) - parsed.astimezone(timezone.utc)
    if age < timedelta(0):
        age = timedelta(0)
    hours = age.total_seconds() / 3600
    status = "Stale" if age > STALE_AFTER else "Fresh"
    return f"{status} ({hours:.1f} hours old)"


def _evidence(label: str, value: object, source: str) -> EvidenceItem:
    """Create a redacted display-safe evidence item."""
    return {
        "label": redact_sensitive_text(label),
        "value": redact_sensitive_text(str(value)),
        "source": redact_sensitive_text(source),
    }


def _build_answer(
    intent: str,
    direct_answer: str,
    evidence: list[EvidenceItem],
    timestamp: str | None,
    severity: str | None,
    guidance: list[str],
    sufficient: bool,
    now: datetime | None,
) -> AssistantAnswer:
    """Build and redact the common assistant response contract."""
    return {
        "intent": intent,
        "direct_answer": redact_sensitive_text(direct_answer),
        "evidence": evidence,
        "relevant_timestamp": timestamp,
        "severity": severity,
        "guidance": [redact_sensitive_text(item) for item in guidance],
        "sufficient_evidence": sufficient,
        "freshness": data_freshness(timestamp, now),
    }


def _unavailable(
    intent: str,
    missing: str,
    guidance: str,
    now: datetime | None,
) -> AssistantAnswer:
    """Return an explicit insufficient-evidence response."""
    return _build_answer(
        intent,
        f"There is not enough collected evidence to answer this yet: {missing}.",
        [_evidence("Unavailable evidence", missing, "FixMate AI database")],
        None,
        None,
        [guidance],
        False,
        now,
    )


def _highest_severity(issues: list[dict[str, Any]]) -> str | None:
    """Return the highest known issue severity."""
    severities = [str(issue.get("severity") or "").lower() for issue in issues]
    return max(severities, key=lambda value: SEVERITY_ORDER.get(value, 0), default=None)


def _answer_computer_slow(database_path: Path, database_url: str | None = None, now: datetime | None = None) -> AssistantAnswer:
    scan = get_latest_health_scan(database_path, database_url=database_url)
    if scan is None:
        return _unavailable("computer_slow", "no system-health scan exists", "Guidance: run a new System Health scan while the slowdown is happening.", now)

    cpu = scan.get("cpu_percent")
    memory = scan.get("memory_percent")
    history = get_health_scan_history(database_path=database_path, database_url=database_url)
    recent_resource_issues = [
        issue
        for issue in get_issue_history(limit=30, database_path=database_path, database_url=database_url)
        if issue.get("code") in {"CPU_HIGH", "MEMORY_HIGH"}
    ]
    current_high = []
    if isinstance(cpu, (int, float)) and cpu > 90:
        current_high.append("CPU")
    if isinstance(memory, (int, float)) and memory > 85:
        current_high.append("memory")

    evidence = [
        _evidence("Latest CPU usage", f"{cpu:.1f}%" if isinstance(cpu, (int, float)) else "Unavailable", "Latest system scan"),
        _evidence("Latest memory usage", f"{memory:.1f}%" if isinstance(memory, (int, float)) else "Unavailable", "Latest system scan"),
    ]
    historical_cpu = [row["cpu_percent"] for row in history if isinstance(row.get("cpu_percent"), (int, float))]
    historical_memory = [row["memory_percent"] for row in history if isinstance(row.get("memory_percent"), (int, float))]
    if historical_cpu:
        evidence.append(_evidence("Recent recorded CPU peak", f"{max(historical_cpu):.1f}%", "System scan history"))
    if historical_memory:
        evidence.append(_evidence("Recent recorded memory peak", f"{max(historical_memory):.1f}%", "System scan history"))

    if current_high:
        direct = f"The latest scan shows high {' and '.join(current_high)}, which can contribute to the recorded slowdown."
        severity = "high"
        sufficient = True
    elif recent_resource_issues:
        direct = "The evidence is mixed: the latest scan is below the alert thresholds, but an earlier scan recorded high resource usage. The data does not prove the current cause."
        severity = _highest_severity(recent_resource_issues)
        evidence.append(_evidence("Earlier detected issue", recent_resource_issues[0]["evidence"], "Issue history"))
        sufficient = False
    else:
        direct = "The latest scan does not show CPU or memory above FixMate AI's alert thresholds, so the collected data does not establish why the computer feels slow."
        severity = None
        sufficient = False

    return _build_answer(
        "computer_slow",
        direct,
        evidence,
        scan["collected_at"],
        severity,
        [
            "Guidance: run another System Health scan while the slowdown is occurring.",
            "Guidance: review the recorded top processes and close only applications you recognize and no longer need.",
        ],
        sufficient,
        now,
    )


def _answer_memory(database_path: Path, database_url: str | None = None, now: datetime | None = None) -> AssistantAnswer:
    result = get_top_resource_processes(database_path=database_path, database_url=database_url)
    if result is None:
        return _unavailable("memory_usage", "no system-health scan exists", "Guidance: run a new System Health scan.", now)
    processes = result["processes"]
    if not processes:
        return _build_answer(
            "memory_usage",
            "The latest scan exists, but process memory details were unavailable.",
            [_evidence("Process list", "Unavailable", "Latest system scan")],
            result["collected_at"],
            None,
            ["Guidance: rerun the scan; some operating-system permissions can temporarily hide process metrics."],
            False,
            now,
        )
    top = processes[0]
    evidence = [
        _evidence(
            f"Process #{index}",
            f"{item.get('name', 'Unknown')} — {float(item.get('memory_mb') or 0):.1f} MB",
            "Latest system scan",
        )
        for index, item in enumerate(processes[:5], start=1)
    ]
    return _build_answer(
        "memory_usage",
        f"{top.get('name', 'Unknown')} used the most recorded memory in the latest scan at {float(top.get('memory_mb') or 0):.1f} MB.",
        evidence,
        result["collected_at"],
        None,
        ["Guidance: close only applications you recognize and no longer need; do not terminate unfamiliar system processes."],
        True,
        now,
    )


def _answer_disk(database_path: Path, database_url: str | None = None, now: datetime | None = None) -> AssistantAnswer:
    disk = get_disk_status(database_path, database_url=database_url)
    if disk is None:
        return _unavailable("disk_status", "no disk scan exists", "Guidance: run a new System Health scan.", now)
    free = disk.get("disk_free_percent")
    used = disk.get("disk_used_percent")
    if free is None:
        return _build_answer(
            "disk_status",
            "A scan exists, but disk free-space evidence was unavailable.",
            [_evidence("Disk free space", "Unavailable", "Latest system scan")],
            disk["collected_at"],
            None,
            ["Guidance: rerun the System Health scan and check the operating system's storage view."],
            False,
            now,
        )
    nearly_full = bool(disk["nearly_full"])
    return _build_answer(
        "disk_status",
        (f"Yes. Only {float(free):.1f}% disk space was free in the latest scan." if nearly_full else f"No. The latest scan recorded {float(free):.1f}% free disk space, above the 10% alert threshold."),
        [
            _evidence("Disk free", f"{float(free):.1f}%", "Latest system scan"),
            _evidence("Disk used", f"{float(used):.1f}%" if isinstance(used, (int, float)) else "Unavailable", "Latest system scan"),
        ],
        disk["collected_at"],
        "medium" if nearly_full else None,
        ["Guidance: use the operating system's storage tools to review large categories; do not delete unfamiliar system files."],
        True,
        now,
    )


def _answer_network(
    intent: str,
    database_path: Path,
    database_url: str | None = None,
    now: datetime | None = None,
) -> AssistantAnswer:
    network = get_network_status(database_path, database_url=database_url)
    if network is None:
        return _unavailable(intent, "no network diagnostic exists", "Guidance: open Network Diagnostics and run a new diagnostic.", now)
    latency = network.get("latency_ms")
    threshold = network.get("latency_threshold_ms")
    evidence = [
        _evidence("Active interfaces", network.get("active_interface_count", 0), "Latest network diagnostic"),
        _evidence("Internet connectivity", "Online" if network["internet_connected"] else "Offline", "Latest network diagnostic"),
        _evidence("Timed out", "Yes" if network["timed_out"] else "No", "Latest network diagnostic"),
        _evidence("Latency", f"{float(latency):.2f} ms" if isinstance(latency, (int, float)) else "Unavailable", "Latest network diagnostic"),
    ]
    issues = list(network.get("issues", []))
    severity = _highest_severity(issues)
    if intent == "internet_status":
        direct = (
            "Yes. The latest diagnostic established its configured internet connection."
            if network["internet_connected"]
            else "No. The latest diagnostic could not establish its configured internet connection."
        )
        sufficient = True
    elif not isinstance(latency, (int, float)):
        direct = "The latest diagnostic has no successful latency measurement, so there is not enough evidence to determine whether the network is slow."
        sufficient = False
    elif isinstance(threshold, (int, float)) and latency > threshold:
        direct = f"The latest latency was {latency:.2f} ms, above the configured {threshold:.2f} ms threshold."
        severity = severity or "medium"
        sufficient = True
    else:
        direct = f"The latest latency was {latency:.2f} ms and did not exceed the configured threshold; the recorded data does not show high latency."
        sufficient = True
    return _build_answer(
        intent,
        direct,
        evidence,
        network["collected_at"],
        severity,
        [
            "Guidance: rerun the diagnostic when the problem is happening because connectivity can change quickly.",
            "Guidance: do not disable firewall or security software based only on this result.",
        ],
        sufficient,
        now,
    )


def _answer_today(database_path: Path, database_url: str | None = None, now: datetime | None = None) -> AssistantAnswer:
    current = now or datetime.now().astimezone()
    start = current.replace(hour=0, minute=0, second=0, microsecond=0)
    issues = get_recent_issues(since=start, database_path=database_path, database_url=database_url)
    latest = generate_health_summary(database_path, database_url=database_url).get("latest_data_timestamp")
    if not issues:
        return _build_answer(
            "issues_today",
            "No issues were recorded today. This means no stored rule fired; it does not prove the computer had no problems.",
            [_evidence("Recorded issues today", 0, "System and network issue history")],
            latest,
            None,
            ["Guidance: run fresh health and network diagnostics if you need current evidence."],
            bool(latest),
            now,
        )
    evidence = [
        _evidence(issue["code"], issue["evidence"], f"{issue['source']} issue at {issue['timestamp']}")
        for issue in issues[:10]
    ]
    return _build_answer(
        "issues_today",
        f"FixMate AI recorded {len(issues)} issue{'s' if len(issues) != 1 else ''} today.",
        evidence,
        issues[0]["timestamp"],
        _highest_severity(issues),
        ["Guidance: review the highest-severity issue first and verify it with a fresh scan before making changes."],
        True,
        now,
    )


def _answer_screenshot(database_path: Path, database_url: str | None = None, now: datetime | None = None) -> AssistantAnswer:
    analysis = get_screenshot_analysis(database_path, database_url=database_url)
    if analysis is None:
        return _unavailable("screenshot_error", "no screenshot analysis exists", "Guidance: use Error Screenshot Analyzer, review its OCR text, and run analysis.", now)
    issue_id = analysis.get("matched_issue_id")
    if not issue_id:
        return _build_answer(
            "screenshot_error",
            "The latest screenshot analysis did not produce a reliable knowledge-base match.",
            [_evidence("Reliable top match", "None", "Latest screenshot analysis")],
            analysis["analyzed_at"],
            None,
            ["Guidance: correct OCR mistakes and consult the affected software's official documentation."],
            False,
            now,
        )
    entry = next((item for item in load_knowledge_base() if item["id"] == issue_id), None)
    if entry is None:
        return _build_answer(
            "screenshot_error",
            "The stored match no longer exists in the local knowledge base, so it cannot be explained reliably.",
            [_evidence("Stored issue ID", issue_id, "Latest screenshot analysis")],
            analysis["analyzed_at"],
            None,
            ["Guidance: rerun the screenshot analysis with the current knowledge base."],
            False,
            now,
        )
    return _build_answer(
        "screenshot_error",
        f"The latest screenshot analysis most reliably matched: {entry['title']}.",
        [
            _evidence("Matched issue", entry["title"], "Latest screenshot analysis"),
            _evidence("Confidence", f"{float(analysis.get('confidence_score') or 0):.1f}%", "Latest screenshot analysis"),
            _evidence("OCR text handling", "Stored text was redacted and treated as untrusted data", "Privacy controls"),
        ],
        analysis["analyzed_at"],
        entry["severity"],
        [f"Guidance: {step}" for step in entry["troubleshooting_steps"]],
        True,
        now,
    )


def _answer_summary(database_path: Path, database_url: str | None = None, now: datetime | None = None) -> AssistantAnswer:
    summary = generate_health_summary(database_path, database_url=database_url)
    scan = summary["latest_health"]
    if scan is None:
        return _unavailable("health_summary", "no system-health scan exists", "Guidance: run a new System Health scan, then optionally run Network Diagnostics.", now)
    evidence = [
        _evidence("Health score", f"{scan['health_score']}/100", "Latest system scan"),
        _evidence("CPU", f"{scan['cpu_percent']:.1f}%" if scan.get("cpu_percent") is not None else "Unavailable", "Latest system scan"),
        _evidence("Memory", f"{scan['memory_percent']:.1f}%" if scan.get("memory_percent") is not None else "Unavailable", "Latest system scan"),
        _evidence("Disk free", f"{scan['disk_free_percent']:.1f}%" if scan.get("disk_free_percent") is not None else "Unavailable", "Latest system scan"),
    ]
    network = summary["network"]
    if network:
        evidence.append(_evidence("Internet", "Online" if network["internet_connected"] else "Offline", "Latest network diagnostic"))
    else:
        evidence.append(_evidence("Network evidence", "No diagnostic recorded", "Network diagnostics"))
    issues = summary["recent_issues"]
    direct = f"The latest system health score is {scan['health_score']}/100. FixMate AI has {len(issues)} recorded system or network issue{'s' if len(issues) != 1 else ''} in recent history."
    return _build_answer(
        "health_summary",
        direct,
        evidence,
        summary["latest_data_timestamp"],
        _highest_severity(issues),
        ["Guidance: refresh system and network diagnostics before relying on older evidence."],
        True,
        now,
    )


def _answer_priority(database_path: Path, database_url: str | None = None, now: datetime | None = None) -> AssistantAnswer:
    issues = get_issue_history(limit=100, database_path=database_path, database_url=database_url)
    if not issues:
        return _build_answer(
            "fix_priority",
            "No stored system or network issue currently provides evidence for a repair priority.",
            [_evidence("Recorded issues", 0, "Issue history")],
            generate_health_summary(database_path, database_url=database_url).get("latest_data_timestamp"),
            None,
            ["Guidance: run fresh System Health and Network Diagnostics checks before deciding what to fix."],
            False,
            now,
        )
    first = max(
        issues,
        key=lambda issue: (
            SEVERITY_ORDER.get(str(issue.get("severity") or "").lower(), 0),
            str(issue.get("timestamp") or ""),
        ),
    )
    return _build_answer(
        "fix_priority",
        f"Based on recorded severity, address {str(first['code']).replace('_', ' ').lower()} first. This is guidance, not a guaranteed fix.",
        [
            _evidence("Highest-priority issue", first["evidence"], f"{first['source']} issue"),
            _evidence("Why it ranks first", f"Severity: {first['severity']}", "Deterministic severity ordering"),
        ],
        first["timestamp"],
        first["severity"],
        [f"Guidance: {first['recommendation']}", "Guidance: confirm the issue with a fresh scan before changing anything."],
        True,
        now,
    )


def _answer_knowledge(
    question: str,
    entries: list[KnowledgeEntry],
    now: datetime | None,
) -> AssistantAnswer | None:
    matches = search_knowledge_base(question, entries=entries)
    if not matches:
        return None
    match = matches[0]
    issue = match["issue"]
    return _build_answer(
        "knowledge_search",
        f"The question most reliably matches the local knowledge-base topic: {issue['title']}.",
        [
            _evidence("Knowledge-base match", issue["title"], "Local error knowledge base"),
            _evidence("Matching confidence", f"{match['confidence']:.1f}%", "Deterministic text matching"),
        ],
        None,
        issue["severity"],
        [f"Guidance: {step}" for step in issue["troubleshooting_steps"]],
        True,
        now,
    )


def answer_question(
    question: str,
    database_path: Path = DEFAULT_DB_PATH,
    now: datetime | None = None,
    knowledge_entries: list[KnowledgeEntry] | None = None,
    database_url: str | None = DEFAULT_DATABASE_URL,
) -> AssistantAnswer:
    """Route an untrusted question and answer only from collected local evidence."""
    intent = detect_intent(question)
    if intent == "computer_slow":
        return _answer_computer_slow(database_path=database_path, now=now, database_url=database_url)
    if intent == "memory_usage":
        return _answer_memory(database_path=database_path, now=now, database_url=database_url)
    if intent == "disk_status":
        return _answer_disk(database_path=database_path, now=now, database_url=database_url)
    if intent in {"internet_status", "network_slow"}:
        return _answer_network(intent=intent, database_path=database_path, now=now, database_url=database_url)
    if intent == "issues_today":
        return _answer_today(database_path=database_path, now=now, database_url=database_url)
    if intent == "screenshot_error":
        return _answer_screenshot(database_path=database_path, now=now, database_url=database_url)
    if intent == "health_summary":
        return _answer_summary(database_path=database_path, now=now, database_url=database_url)
    if intent == "fix_priority":
        return _answer_priority(database_path=database_path, now=now, database_url=database_url)

    entries = knowledge_entries if knowledge_entries is not None else load_knowledge_base()
    knowledge_answer = _answer_knowledge(question, entries, now)
    if knowledge_answer is not None:
        return knowledge_answer
    return _build_answer(
        "unknown",
        "I cannot answer that from the supported FixMate AI evidence routes.",
        [_evidence("Routing result", "No supported intent or reliable knowledge-base match", "Deterministic router")],
        None,
        None,
        [
            "Guidance: ask about system slowness, memory, disk space, internet, latency, today's issues, the latest screenshot result, health summary, or repair priority."
        ],
        False,
        now,
    )
