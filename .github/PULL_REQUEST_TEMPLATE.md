## What does this PR do?

<!-- One-line description of the change -->

## Type of Change

- [ ] Bug fix
- [ ] New standard or config
- [ ] New or updated workflow template
- [ ] Documentation
- [ ] Chore / dependency update

## Checklist

- [ ] CHANGELOG.md has been updated or this change is not user-facing
- [ ] If a new workflow template was added, it is listed in README.md
- [ ] If a new template was added, it is referenced in `docs/repo-standard-v1.md` where appropriate
- [ ] Python scripts compile: `python3 -m py_compile scripts/*.py`
- [ ] Docs / AI-rule sync check passes: `python3 scripts/check_docs_ai_rule_sync.py --base-ref main`
- [ ] MkDocs dependencies install: `python3 -m pip install -r requirements-docs.txt`
- [ ] MkDocs strict build passes: `mkdocs build --strict`
- [ ] Commit messages follow Conventional Commits (`type(scope): description`)

## Related Issues

Closes #
