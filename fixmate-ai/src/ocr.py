"""Local Tesseract OCR integration with graceful failure handling."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytesseract


@dataclass(frozen=True)
class OcrResult:
    """Text or a user-safe OCR error; no exception needs to reach the UI."""

    text: str
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        """Return whether OCR completed without an integration error."""
        return self.error is None


def configure_tesseract() -> str:
    """Configure pytesseract from TESSERACT_CMD or the executable PATH."""
    configured = os.environ.get("TESSERACT_CMD", "").strip()
    if configured:
        command = str(Path(configured).expanduser())
        pytesseract.pytesseract.tesseract_cmd = command
        return command
    discovered = shutil.which("tesseract")
    if discovered:
        pytesseract.pytesseract.tesseract_cmd = discovered
        return discovered
    return ""


def is_tesseract_available() -> bool:
    """Return whether a configured Tesseract executable can be found."""
    command = configure_tesseract()
    return bool(command and Path(command).is_file())


def extract_text(image: np.ndarray, timeout_seconds: float = 15.0) -> OcrResult:
    """Extract text locally and convert known OCR failures to safe messages."""
    configure_tesseract()
    try:
        text = pytesseract.image_to_string(
            image,
            config="--psm 6",
            timeout=max(1.0, min(float(timeout_seconds), 30.0)),
        )
        return OcrResult(text=text.strip())
    except pytesseract.TesseractNotFoundError:
        return OcrResult(
            text="",
            error=(
                "Tesseract OCR is not installed or configured. You can still type "
                "the error message manually before analysis."
            ),
        )
    except RuntimeError:
        return OcrResult(
            text="",
            error="OCR exceeded its local time limit. Try a smaller or clearer image.",
        )
    except (pytesseract.TesseractError, OSError, ValueError):
        return OcrResult(
            text="",
            error="OCR could not read this image. You can enter the error text manually.",
        )

