# Phase 3: Error Screenshot Analyzer

Status: completed and verified.

## Approved goals delivered

- Validates decoded PNG, JPG, and JPEG content up to 5 MB.
- Preprocesses locally with independent OpenCV grayscale, contrast, denoising, and optional threshold functions.
- Extracts editable text with local Tesseract through `pytesseract`.
- Handles missing Tesseract and OCR timeouts without crashing.
- Matches normalized text against 15 local Windows and Ubuntu troubleshooting entries.
- Returns deterministic rankings, confidence scores, and matching-text evidence.
- Uses a 60% reliability floor and displays “No reliable match found” below it.
- Stores only anonymized metadata and privacy-redacted text.
- Never stores screenshot files or image bytes.
- Adds a separate Streamlit analyzer page with previews, editable text, results, privacy guidance, and history.
- Preserves all Phase 1 and Phase 2 records through a named additive migration.
- Uses generated images and mocked OCR; automated tests need neither Tesseract nor internet access.

## Implemented files

- `pages/2_Error_Screenshot_Analyzer.py`
- `src/image_processing.py`
- `src/ocr.py`
- `src/error_matcher.py`
- `src/knowledge_base.py`
- `src/privacy.py`
- `data/error_knowledge_base.json`
- Phase 3 unit and migration tests under `tests/`

## Database migration

Migration ID: `phase3_screenshot_analyzer`.

The `screenshot_analyses` table stores analysis time, an anonymized image identifier, redacted extracted text, the top reliable issue ID, and confidence. It has no image or image-path column. Existing system scans, system issues, network diagnostics, and network issues remain unchanged.

## Dependencies

- `opencv-python-headless`
- `Pillow`
- `pytesseract`
- `numpy`

The Tesseract executable is a separate optional local installation. The main application and manual analyzer text entry work when it is absent.

## Verification

- Complete Phase 1–3 test suite passes.
- OCR and network operations are mocked in tests.
- Streamlit main dashboard and analyzer page are validated independently.
