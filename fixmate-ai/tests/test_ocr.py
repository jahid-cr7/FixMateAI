"""Tests for local OCR behavior without requiring Tesseract."""

from __future__ import annotations

import numpy as np
import pytest
from pathlib import Path

from src import ocr


def test_mocked_ocr_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """OCR text should be trimmed when the integration is mocked successful."""
    monkeypatch.setattr(ocr, "configure_tesseract", lambda: "mock-tesseract")
    monkeypatch.setattr(
        ocr.pytesseract,
        "image_to_string",
        lambda image, config, timeout: "  Access denied\n",
    )
    result = ocr.extract_text(np.zeros((10, 10), dtype=np.uint8))
    assert result.succeeded is True
    assert result.text == "Access denied"


def test_missing_tesseract_is_handled(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing executable should return guidance rather than crash."""
    monkeypatch.setattr(ocr, "configure_tesseract", lambda: "")

    def missing(*args: object, **kwargs: object) -> str:
        raise ocr.pytesseract.TesseractNotFoundError()

    monkeypatch.setattr(ocr.pytesseract, "image_to_string", missing)
    result = ocr.extract_text(np.zeros((10, 10), dtype=np.uint8))
    assert result.succeeded is False
    assert "not installed" in str(result.error)


def test_ocr_timeout_is_handled(monkeypatch: pytest.MonkeyPatch) -> None:
    """A mocked OCR timeout should become a user-safe result."""
    monkeypatch.setattr(ocr, "configure_tesseract", lambda: "mock-tesseract")

    def time_out(*args: object, **kwargs: object) -> str:
        raise RuntimeError("simulated timeout")

    monkeypatch.setattr(ocr.pytesseract, "image_to_string", time_out)
    result = ocr.extract_text(np.zeros((10, 10), dtype=np.uint8))
    assert result.succeeded is False
    assert "time limit" in str(result.error)


def test_configured_mock_executable_is_detected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """TESSERACT_CMD should support an explicitly configured executable path."""
    executable = tmp_path / "tesseract-mock.exe"
    executable.write_text("mock", encoding="utf-8")
    monkeypatch.setenv("TESSERACT_CMD", str(executable))
    assert ocr.is_tesseract_available() is True
