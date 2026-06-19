# AGENTS.md

## Project purpose

FixMate AI is a beginner-friendly, portfolio-quality system and network health dashboard for Windows and Ubuntu. Keep the application read-only and safe by default.

## Commands

Run these from the `fixmate-ai` directory with the virtual environment activated:

```bash
python -m pip install -r requirements.txt
python -m pytest
python -m streamlit run app.py
```

## Conventions

- Support Python 3.11 and newer.
- Use type hints and docstrings for public functions.
- Use `pathlib.Path` for filesystem paths.
- Keep collection, detection, persistence, scoring, and presentation separate.
- Detection rules must be pure functions tested with simulated values.
- Mock every network operation in tests; the suite must work offline.
- Keep connectivity timeouts short and bounded so the dashboard stays responsive.
- Handle missing or permission-restricted metrics without crashing.
- Use parameterized SQLite queries; never build SQL with user input.
- Apply named, additive database migrations; never delete existing records during startup.
- Keep recommendations explanatory and non-destructive.
- Do not collect passwords, browser history, personal documents, or file contents.
- Do not scan ports, capture packets, or display complete MAC addresses.
- Do not terminate processes, execute repairs, change settings, or require administrator/root privileges.
- Do not commit databases, virtual environments, caches, or local secrets.
- Avoid OS-specific behavior. Isolate it behind a clearly named helper if unavoidable.

## Before submitting changes

1. Run `python -m pytest`.
2. Start Streamlit and check both dashboard tabs for visible errors.
3. Confirm `data/fixmate.db` remains ignored by Git.
4. Update `README.md` when setup steps or behavior change.

## Deferred work

Phase 3 is design-only. See `docs/PHASE3_PLAN.md`; do not add OCR dependencies or implementation until explicitly approved.
