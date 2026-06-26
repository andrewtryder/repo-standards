# Python Rules

Use the existing dependency workflow unless the task explicitly migrates package management.

Preferred checks:

- `ruff format --check .`
- `ruff check .`
- `pytest`
- `coverage run -m pytest && coverage report`

Use Ruff for formatting/linting and pytest for tests when configured.
File patterns determine execution: Python checks apply to `*.py` files when those files exist.

## Related docs

- `docs/profiles.md`
- `docs/code-quality-standards.md`
- `docs/ai-rules-maintenance.md`
- `docs/detection.md`
- `docs/deployment/gcp.md`
