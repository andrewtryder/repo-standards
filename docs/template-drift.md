# Template Drift Management

## The problem

Repo-standards templates (workflows, configs, repo policies) evolve over time. When repos copy templates, those copies can drift from the canonical version. Without a drift management strategy, repos silently fall behind on improvements and fixes.

## Two approaches

### A. Copied templates (for early migration)

During initial migration, repos **copy** templates from `templates/workflows/*.yml` into their `.github/workflows/` directory.

**Pros:**
- Simple to understand and execute.
- No infrastructure dependencies.
- Each repo can customize independently.

**Cons:**
- Templates drift from the canonical source over time.
- Must be reassessed when repo-standards changes.
- No automatic update path.

**When to use:** Initial migration, early adoption, repos with low change frequency.

**How to manage drift:**
- Re-run the assessment script (`scripts/assess_repo_standards_migration_v3.py`) whenever repo-standards changes.
- Compare copied workflows against canonical templates manually or via diff.
- Subscribe to repo-standards release notes.

### B. GitHub reusable workflows (for long-term drift reduction)

The **preferred long-term approach** is to define CI workflows as GitHub reusable workflows in the repo-standards repo and have downstream repos call them with minimal configuration.

**Pros:**
- Single source of truth for workflow logic.
- Updates flow automatically to all consumers.
- Reduces boilerplate in each repo.

**Cons:**
- Requires reusable workflow files in repo-standards.
- Downstream repos lose some customization flexibility.
- Requires coordinating shared workflow changes across repos.

**When to use:** After the standard is stable, for repos with active development.

### Reusable workflow caller examples

#### Node CI caller

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  node-ci:
    uses: andrewtryder/repo-standards/.github/workflows/node-ci.reusable.yml@main
    with:
      node_version: "24"
      install_command: "npm ci"
      format_check_command: "npm run format:check"
      lint_command: "npm run lint"
      typecheck_command: "npm run typecheck"
      test_command: "npm test"
      coverage_command: "npm run test:coverage"
      build_command: "npm run build"
```

#### Python CI caller

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  python-ci:
    uses: andrewtryder/repo-standards/.github/workflows/python-ci.reusable.yml@main
    with:
      python_version: "3.12"
      install_command: "python -m pip install -r requirements.txt -r requirements-dev.txt"
      lint_command: "ruff check ."
      format_check_command: "ruff format --check ."
      test_command: "coverage run -m pytest"
      coverage_args: "--report-only"
```

### Reusable workflow templates

The reusable workflow templates are at:

- `templates/workflows/node-ci.reusable.yml` — reusable Node CI workflow
- `templates/workflows/python-ci.reusable.yml` — reusable Python CI workflow

These are designed to be hosted in the repo-standards repo and called from downstream repos.

## Summary

| Aspect | Copied templates | Reusable workflows |
|---|---|---|
| Migration speed | Fast | Slower (need to wire up) |
| Drift risk | High | Low |
| Customization | Full | Constrained by inputs |
| Update path | Manual re-copy | Automatic on ref update |
| Long-term viability | Low | High |

**Recommendation:** Use copied templates for the initial migration wave. Transition to reusable workflows once the standard stabilizes.

## Docs and AI rule drift

Template drift is not limited to workflows. Human-facing docs (`docs/`, `README.md`), repo policy templates, and `ai/rules/*.md` can also drift apart.

The **Docs / AI Rule Sync** check warns when docs, templates, profiles, or standards files change without corresponding AI rule source changes. It is warning-only by default. Repos may make it strict after the standard stabilizes.

```bash
python3 scripts/check_docs_ai_rule_sync.py --base-ref main
python3 scripts/check_docs_ai_rule_sync.py --base-ref main --strict
```

Copy `templates/workflows/docs-ai-rule-sync.yml` to enable this in CI. See [`ai-rules-maintenance.md`](ai-rules-maintenance.md) for the full governance pipeline.