# Phase 3 Plan: Error Screenshot Analyzer

Status: planned only. Do not implement until explicitly approved.

## Scope

- Validate PNG, JPG, and JPEG uploads by size and decoded image content.
- Preprocess images locally with independent OpenCV grayscale, contrast, denoising, and thresholding functions.
- Extract editable text with local Tesseract through `pytesseract`, with safe missing-installation and timeout handling.
- Match normalized text against a local JSON knowledge base containing at least 15 Windows and Ubuntu problems.
- Rank reliable matches with confidence scores and matching-text evidence; never invent unmatched solutions.
- Store analysis metadata and privacy-redacted OCR text without storing uploaded screenshots.
- Add a separate Streamlit analyzer page with previews, privacy guidance, ranked results, and history.
- Add generated-image, mocked-OCR, matcher, and migration tests that require neither Tesseract nor internet access.

## Planned files

- `pages/2_Error_Screenshot_Analyzer.py`
- `src/image_processing.py`
- `src/ocr.py`
- `src/error_matcher.py`
- `src/knowledge_base.py`
- `src/privacy.py`
- `data/error_knowledge_base.json`
- Corresponding unit and migration tests

## Planned database migration

Add a `screenshot_analyses` table through the versioned migration system. Store the timestamp, anonymized filename, privacy-redacted extracted text, top matched issue ID, and confidence score. Preserve all system-health and network records. Never store uploaded image files by default.

## Planned dependencies

- `opencv-python-headless`
- `Pillow`
- `pytesseract`
- `numpy`

Tesseract remains a separately installed local executable and will be mocked in automated tests.
