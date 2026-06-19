# AGENTS.md

## Project purpose

FixMate AI is a beginner-friendly, portfolio-quality system-health dashboard for Windows and Ubuntu. Keep the application read-only and safe by default.

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
- Keep metric collection, detection, persistence, scoring, and presentation separate.
- Detection rules must be pure functions tested with simulated values.
- Handle missing or permission-restricted metrics without crashing.
- Use parameterized SQLite queries; never build SQL with user input.
- Keep recommendations explanatory and non-destructive.
- Do not collect passwords, browser history, personal documents, or file contents.
- Do not terminate processes, change settings, or require administrator/root privileges.
- Do not commit database files, virtual environments, caches, or local secrets.
- Avoid OS-specific behavior. If it becomes necessary, isolate it behind a clearly named helper.

## Before submitting changes

1. Run `python -m pytest`.
2. Start Streamlit and check the dashboard for visible errors.
3. Confirm `data/fixmate.db` remains ignored by Git.
4. Update `README.md` when setup steps or behavior change.
