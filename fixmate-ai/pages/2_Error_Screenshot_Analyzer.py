"""Streamlit page for local OCR and knowledge-base troubleshooting."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from src.database import (
    get_screenshot_analysis_history,
    initialize_database,
    save_screenshot_analysis,
)
from src.error_matcher import ErrorMatch, rank_error_matches, reliable_matches
from src.image_processing import (
    ImageValidationError,
    preprocess_image,
    validate_image,
)
from src.knowledge_base import load_knowledge_base
from src.ocr import extract_text
from src.privacy import anonymize_image_filename, redact_sensitive_text


def _render_matches(matches: list[ErrorMatch]) -> None:
    """Render only reliable, curated matches with evidence and safe steps."""
    reliable = reliable_matches(matches)
    if not reliable:
        st.warning("No reliable match found")
        st.write(
            "The extracted text did not meet the confidence threshold. Check the "
            "text for OCR mistakes or consult the software's official support documentation."
        )
        return

    st.subheader("Ranked troubleshooting results")
    for rank, match in enumerate(reliable[:5], start=1):
        issue = match["issue"]
        with st.expander(
            f"{rank}. {issue['title']} — {match['confidence']:.1f}% confidence",
            expanded=rank == 1,
        ):
            st.progress(int(match["confidence"]))
            st.markdown(f"**Supported OS:** {issue['operating_system']}")
            st.markdown(f"**Severity:** {issue['severity'].title()}")
            st.markdown("**Matching evidence:**")
            for evidence in match["evidence"]:
                st.markdown(f"- {evidence}")
            st.markdown("**Likely causes:**")
            for cause in issue["likely_causes"]:
                st.markdown(f"- {cause}")
            st.markdown("**Safe troubleshooting steps:**")
            for step_number, step in enumerate(issue["troubleshooting_steps"], start=1):
                st.markdown(f"{step_number}. {step}")
            st.caption(issue["documentation_notes"])


def _render_history() -> None:
    """Render redacted metadata from previous analyses."""
    st.subheader("Previous analysis history")
    history = pd.DataFrame(get_screenshot_analysis_history())
    if history.empty:
        st.info("No screenshot analyses have been saved yet.")
        return
    history = history.rename(
        columns={
            "analyzed_at": "Analyzed at",
            "anonymized_filename": "Anonymous image ID",
            "extracted_text_redacted": "Stored redacted text",
            "matched_issue_id": "Top match",
            "confidence_score": "Confidence",
        }
    )
    history["Stored redacted text"] = history["Stored redacted text"].map(
        lambda value: str(value)[:180] + ("…" if len(str(value)) > 180 else "")
    )
    st.dataframe(history, hide_index=True, width="stretch")


st.set_page_config(
    page_title="Error Screenshot Analyzer — FixMate AI",
    page_icon="🔎",
    layout="wide",
)
initialize_database()

st.title("🔎 Error Screenshot Analyzer")
st.caption("Local image preprocessing, OCR, and curated troubleshooting guidance")
st.warning(
    "Privacy reminder: screenshots may contain names, email addresses, paths, "
    "passwords, or tokens. Crop or redact sensitive details before uploading. "
    "Processing stays on this computer and screenshot files are never saved."
)
st.info(
    "Text extracted from an image is treated only as untrusted error text. "
    "FixMate AI never executes commands or follows instructions found in screenshots."
)

try:
    knowledge_base = load_knowledge_base()
except (OSError, ValueError) as error:
    st.error(f"The local troubleshooting knowledge base could not be loaded: {error}")
    st.stop()

uploaded_file = st.file_uploader(
    "Upload an error screenshot (maximum 5 MB)",
    type=["png", "jpg", "jpeg"],
    help="The file is validated by decoded image content, not only its filename.",
)
use_threshold = st.checkbox(
    "Apply thresholding for clearer text",
    value=True,
    help="Disable this when the screenshot has colored text that becomes harder to read.",
)

if uploaded_file is not None:
    image_bytes = uploaded_file.getvalue()
    try:
        validated = validate_image(image_bytes)
    except ImageValidationError as error:
        st.error(str(error))
    else:
        anonymous_filename = anonymize_image_filename(
            image_bytes, validated.image_format
        )
        if st.session_state.get("analyzer_image_id") != anonymous_filename:
            st.session_state.analyzer_image_id = anonymous_filename
            st.session_state.analyzer_ocr_text = ""
            st.session_state.analyzer_matches = None

        processed = preprocess_image(validated.image, use_threshold=use_threshold)
        original_column, processed_column = st.columns(2)
        with original_column:
            st.subheader("Original image")
            st.image(validated.image, width="stretch")
            st.caption(
                f"Validated {validated.image_format} · {validated.width} × {validated.height}"
            )
        with processed_column:
            st.subheader("Processed image")
            st.image(processed, width="stretch", clamp=True)
            st.caption("Grayscale · contrast enhanced · denoised" + (" · thresholded" if use_threshold else ""))

        if st.button("Extract text with local OCR", type="primary"):
            with st.spinner("Running Tesseract locally..."):
                ocr_result = extract_text(processed)
            if ocr_result.succeeded:
                st.session_state.analyzer_ocr_text = ocr_result.text
                if ocr_result.text:
                    st.success("OCR completed. Review and edit the text before analysis.")
                else:
                    st.warning("OCR completed but found no text. Enter the error manually.")
            else:
                st.warning(ocr_result.error)

        st.text_area(
            "Extracted error text (editable)",
            key="analyzer_ocr_text",
            height=180,
            placeholder="OCR text will appear here, or type the error message manually.",
        )

        if st.button("Analyze error text"):
            editable_text = st.session_state.analyzer_ocr_text.strip()
            if not editable_text:
                st.error("Enter or extract an error message before analysis.")
            else:
                matches = rank_error_matches(editable_text, knowledge_base)
                reliable = reliable_matches(matches)
                top_match = reliable[0] if reliable else None
                analyzed_at = datetime.now().astimezone().isoformat(timespec="seconds")
                save_screenshot_analysis(
                    analyzed_at=analyzed_at,
                    anonymized_filename=anonymous_filename,
                    extracted_text_redacted=redact_sensitive_text(editable_text),
                    matched_issue_id=(
                        top_match["issue"]["id"] if top_match is not None else None
                    ),
                    confidence_score=(
                        top_match["confidence"] if top_match is not None else None
                    ),
                )
                st.session_state.analyzer_matches = matches
                st.success("Analysis completed. Only redacted text and metadata were saved.")

        saved_matches = st.session_state.get("analyzer_matches")
        if saved_matches is not None:
            _render_matches(saved_matches)

        del processed
        del image_bytes

_render_history()

st.caption(
    "FixMate AI provides curated troubleshooting guidance, not guaranteed diagnosis. "
    "Verify important actions in official documentation and back up important data first."
)
