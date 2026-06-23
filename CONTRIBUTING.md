# Contributing

Thank you for your interest in contributing to repo-standards.

## How to contribute

1. Fork the repository (if external) or create a feature branch from `main`.
2. Follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages (`feat:`, `fix:`, `chore:`, `docs:`, etc.).
3. Run local checks before opening a pull request:

```bash
python3 -m py_compile scripts/*.py
python3 scripts/check_docs_ai_rule_sync.py --base-ref main
python3 -m pip install -r requirements-docs.txt
mkdocs build --strict
```

4. Open a pull request with a clear title and description.

## Pull request guidelines

- Keep PRs focused on a single concern.
- Update `docs/` when behavior or usage changes.
- Update `ai/rules/*.md` when agent/editor behavior changes.
- Update templates when downstream files should change.
- If docs change without AI behavior changes, explain why in the PR body.
- Preserve the phased migration approach: standards PRs should not block useful work over legacy technical debt.

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Questions

Open an issue or discussion on GitHub.
