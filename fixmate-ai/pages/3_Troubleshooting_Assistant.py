"""Streamlit chat page for deterministic evidence-based troubleshooting."""

from __future__ import annotations

import streamlit as st

from src.assistant_tools import generate_health_summary
from src.database import initialize_database
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


def _render_answer(answer: AssistantAnswer) -> None:
    """Render a response with explicit evidence boundaries and guidance labels."""
    st.write(answer["direct_answer"])
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
st.caption("Deterministic answers from collected FixMate AI evidence—no generative AI model")
st.info(
    "Privacy: questions and conversation history stay in this Streamlit session and "
    "are not stored in SQLite or sent to an external service. Questions and OCR text "
    "are treated as untrusted data and are never executed."
)

summary = generate_health_summary()
freshness = data_freshness(summary["latest_data_timestamp"])
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
                _render_answer(message["answer"])

question = st.chat_input("Ask about collected system, network, issue, or screenshot evidence")
pending_question = suggestion if ask_suggestion else question
if pending_question:
    answer = answer_question(pending_question)
    st.session_state.assistant_messages.append(
        {"role": "user", "content": redact_sensitive_text(pending_question)}
    )
    st.session_state.assistant_messages.append(
        {"role": "assistant", "answer": answer}
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
