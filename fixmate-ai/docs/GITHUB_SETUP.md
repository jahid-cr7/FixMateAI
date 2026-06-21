# GitHub Repository Setup

## Suggested repository metadata

**Name:** `fixmate-ai`

**Description:** Local-first Windows and Ubuntu diagnostics with evidence-based troubleshooting, privacy-safe reports, Streamlit, FastAPI, and optional bounded AI explanations.

**Website:** Leave blank unless a real deployed demo exists. Do not link a localhost address.

**Suggested topics:**

```text
python streamlit fastapi sqlite psutil opencv tesseract plotly
system-monitoring troubleshooting privacy docker github-actions portfolio
```

## Suggested pinned-repository text

> Cross-platform IT diagnostics and evidence-based troubleshooting with local history, OCR error analysis, privacy-safe reports, a versioned API, Docker, and Windows/Ubuntu CI. Read-only by design.

## Repository settings

1. Set the default branch to `main`.
2. Enable Issues and use the included templates.
3. Enable private vulnerability reporting if available.
4. Add branch protection for `main` after CI has run successfully:
   - Require pull requests.
   - Require the four CI matrix checks.
   - Require branches to be up to date when appropriate.
5. Do not add repository secrets unless a future workflow genuinely needs them. Current CI requires none.
6. Disable GitHub Actions write permissions; the workflow uses `contents: read`.

## Badges

The README includes version, Python, Streamlit, FastAPI, Docker, CI, tests, and MIT badges. Its CI badge points to:

```text
https://github.com/jahid-cr7/FixMateAI/actions/workflows/ci.yml/badge.svg
```

Verify the workflow badge after the first pushed v1.0.0 commit completes on GitHub Actions.

## First public release

Follow [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md), then create tag `v1.0.0` and a GitHub release using the matching [CHANGELOG.md](CHANGELOG.md) section. Do not attach databases, reports, logs, `.env` files, or unreviewed screenshots as release assets.
