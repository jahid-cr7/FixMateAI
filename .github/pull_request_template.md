## Summary

Describe the focused change and why it is needed.

## Validation

- [ ] `python -m pytest -v` passes from `fixmate-ai/`.
- [ ] Streamlit pages were validated when relevant.
- [ ] FastAPI health, status, and documentation were validated when relevant.
- [ ] Windows and Ubuntu compatibility were considered.
- [ ] Documentation was updated where behavior changed.

## Safety and privacy

- [ ] No secret, `.env`, database, report, log, cache, virtual environment, or private screenshot is included.
- [ ] Test/demo values are clearly synthetic.
- [ ] The change remains read-only and does not add repair execution.
- [ ] OCR text, questions, database values, and provider output remain untrusted data.
- [ ] External transmission, if any, is minimized, redacted, optional, and consent-gated.

## Notes for reviewers

Call out migrations, API contract changes, optional dependencies, or limitations.
