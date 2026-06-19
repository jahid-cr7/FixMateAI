"""Streamlit chat page for deterministic evidence-based troubleshooting."""

from __future__ import annotations

import streamlit as st

from src.assistant_tools import generate_health_summary
from src.database import initialize_database
from src.hybrid_agent import HybridAssistantResult, run_hybrid_assistant
from src.llm import create_provider
from src.privacy import redact_sensitive_text
from src.troubleshooting_assistant import AssistantAnswer, answer_question, data_freshness

SUGGESTED_QUESTIONS = [
    "Why is my computer slow?",
    "What is using the most memory?",
    "Is my disk nearly full?",
    "Is my internet connection working?",
    "Why is my network slow?",
    "What problems were detected today?",
    "Explain my latest screenshot error.",
    "Summarize this computer's health.",
    "What should I fix first?",
]


def _render_answer(
    answer: AssistantAnswer,
    hybrid: HybridAssistantResult | None = None,
) -> None:
    """Render a response with explicit evidence boundaries and guidance labels."""
    st.write(answer["direct_answer"])
    if hybrid is not None and hybrid["ai_generated"]:
        st.markdown(
            f"**AI-generated explanation ({hybrid['provider_name']}):**"
        )
        st.write(hybrid["ai_explanation"])
        st.caption(
            "AI-generated content is explanatory only; deterministic evidence and guidance remain authoritative."
        )
    elif hybrid is not None and hybrid["fallback_used"]:
        st.warning(
            "AI enhancement was unavailable or rejected. The deterministic answer was used instead."
        )
        if hybrid["fallback_reason"]:
            st.caption(hybrid["fallback_reason"])
    metadata = []
    if answer["severity"]:
        metadata.append(f"Severity: {answer['severity'].title()}")
    metadata.append(f"Evidence freshness: {answer['freshness']}")
    if answer["relevant_timestamp"]:
        metadata.append(f"Relevant timestamp: {answer['relevant_timestamp']}")
    else:
        metadata.append("Relevant timestamp: unavailable")
    st.caption(" · ".join(metadata))
    st.markdown("**Guidance (not a guaranteed fix):**")
    for item in answer["guidance"]:
        st.markdown(f"- {item.removeprefix('Guidance: ').removeprefix('guidance: ')}")


def _latest_answer() -> AssistantAnswer | None:
    """Return the newest assistant answer stored only in session state."""
    for message in reversed(st.session_state.assistant_messages):
        if message["role"] == "assistant":
            return message["answer"]
    return None


st.set_page_config(
    page_title="Troubleshooting Assistant — FixMate AI",
    page_icon="💬",
    layout="wide",
)
initialize_database()

if "assistant_messages" not in st.session_state:
    st.session_state.assistant_messages = []

st.title("💬 Troubleshooting Assistant")
st.caption("Deterministic evidence by default, with optional bounded AI explanation")
st.info(
    "Privacy: questions and conversation history stay in this Streamlit session and "
    "are not stored in SQLite or sent to an external service. Questions and OCR text "
    "are treated as untrusted data and are never executed."
)

summary = generate_health_summary()
freshness = data_freshness(summary["latest_data_timestamp"])
provider = create_provider()
provider_status = provider.status

mode = st.radio(
    "Assistant mode",
    ["Deterministic", "AI-enhanced (optional)"],
    horizontal=True,
    help="Deterministic mode is the source of truth and works without any provider.",
)
status_icon = "✅" if provider_status.configured else "ℹ️"
st.write(
    f"{status_icon} **Provider status — {provider_status.name}:** "
    f"{provider_status.message}"
)

external_consent = False
if mode == "AI-enhanced (optional)":
    external_consent = st.checkbox(
        "I consent to sending a redacted question and minimized diagnostic evidence to the configured external provider.",
        value=False,
        disabled=not provider_status.external,
        help="Consent is required only for an external cloud provider, not a loopback Ollama provider.",
    )
    with st.expander("What can be sent to the provider?"):
        st.write(
            "Only the redacted question, deterministic answer fields, timestamps, metrics, "
            "severity, and results from approved read-only tools. Screenshot images, OCR text, "
            "API keys, usernames, process names, complete IP/MAC addresses, and sensitive paths "
            "are excluded."
        )
        st.write(
            "The provider cannot access SQLite, files, the shell, processes, settings, scanning, or repair actions."
        )
freshness_columns = st.columns([2, 1])
freshness_columns[0].metric("Latest collected evidence", freshness)
if summary["latest_data_timestamp"]:
    freshness_columns[1].metric("Latest timestamp", summary["latest_data_timestamp"])
else:
    freshness_columns[1].metric("Latest timestamp", "Unavailable")

st.caption(
    "Need fresher evidence? Open the main FixMate AI page and run a new System Health "
    "scan or Network Diagnostic before asking again."
)
st.markdown(
    "Use **FixMate AI** in the sidebar navigation to open System Health and Network Diagnostics."
)

control_columns = st.columns([4, 1, 1])
suggestion = control_columns[0].selectbox(
    "Suggested questions",
    SUGGESTED_QUESTIONS,
    label_visibility="collapsed",
)
ask_suggestion = control_columns[1].button("Ask suggestion", width="stretch")
if control_columns[2].button("Clear conversation", width="stretch"):
    st.session_state.assistant_messages = []
    st.rerun()

chat_column, evidence_column = st.columns([3, 2])
with chat_column:
    st.subheader("Conversation")
    if not st.session_state.assistant_messages:
        st.write("Ask a supported question to begin.")
    for message in st.session_state.assistant_messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.write(redact_sensitive_text(message["content"]))
            else:
                _render_answer(message["answer"], message.get("hybrid"))

question = st.chat_input("Ask about collected system, network, issue, or screenshot evidence")
pending_question = suggestion if ask_suggestion else question
if pending_question:
    hybrid_result = None
    if mode == "AI-enhanced (optional)":
        hybrid_result = run_hybrid_assistant(
            pending_question,
            provider,
            consent_external=external_consent,
        )
        answer = hybrid_result["answer"]
    else:
        answer = answer_question(pending_question)
    st.session_state.assistant_messages.append(
        {"role": "user", "content": redact_sensitive_text(pending_question)}
    )
    st.session_state.assistant_messages.append(
        {"role": "assistant", "answer": answer, "hybrid": hybrid_result}
    )
    st.rerun()

with evidence_column:
    st.subheader("Evidence panel")
    latest = _latest_answer()
    if latest is None:
        st.info("Evidence used for the latest answer will appear here.")
    else:
        st.metric("Data freshness", latest["freshness"])
        st.write(
            "Evidence status:",
            "Sufficient for this answer" if latest["sufficient_evidence"] else "Insufficient or inconclusive",
        )
        for item in latest["evidence"]:
            with st.container(border=True):
                st.markdown(f"**{item['label']}**")
                st.write(item["value"])
                st.caption(f"Source: {item['source']}")

st.caption(
    "FixMate AI provides guidance from recorded evidence only. It never runs commands, "
    "terminates processes, changes settings, or performs repairs."
)
