# Reusable workflows

Copied workflows are easiest for first adoption. Reusable workflows are preferred long-term because they reduce drift.

Live reusable workflows in this repository:

- `.github/workflows/node-ci.reusable.yml`
- `.github/workflows/python-ci.reusable.yml`
- `.github/workflows/code-quality.reusable.yml` (optional)

Stable consumers should pin to a release tag such as `@v1.3.0`. Use `@main` only for canary repositories that intentionally track unreleased changes.

## When to use each approach

Use copied workflows when:

- the repo has unusual setup
- existing CI is fragile
- deploy behavior is coupled to CI
- this is the first migration PR

Use reusable workflows when:

- the repo's install/lint/test/build commands are clear
- the repo is ready for centralized CI logic
- you want less drift over time

## Node CI caller

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
    uses: andrewtryder/repo-standards/.github/workflows/node-ci.reusable.yml@v1.3.0
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

## Python CI caller

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
    uses: andrewtryder/repo-standards/.github/workflows/python-ci.reusable.yml@v1.3.0
    with:
      python_version: "3.12"
      install_command: "python -m pip install -r requirements.txt -r requirements-dev.txt"
      format_check_command: "ruff format --check ."
      lint_command: "ruff check ."
      test_command: "coverage run -m pytest"
      coverage_args: "--report-only"
```

## Optional file-pattern code quality caller

This workflow runs the read-only file-pattern analyzer from repo-standards. Keep it advisory
during existing-repo migration, then enable `strict` or `run_tools` when the repo is ready.

```yaml
# .github/workflows/code-quality.yml
name: Code quality

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  code-quality:
    uses: andrewtryder/repo-standards/.github/workflows/code-quality.reusable.yml@v1.3.0
    with:
      strict: false
      run_tools: false
      python_enabled: true
      shell_enabled: true
      yaml_enabled: true
      markdown_enabled: true
      docker_enabled: true
      make_enabled: true
```

Optional command inputs include `python_lint_command`, `shell_lint_command`,
`yaml_lint_command`, `markdown_check_command`, `docker_lint_command`, and
`make_lint_command`. Use check-only commands.

## Workflow locations

| Path | Purpose |
|---|---|
| `.github/workflows/*.reusable.yml` | Live reusable workflows callable by downstream repos |
| `templates/workflows/*.reusable.yml` | Copy/reference templates, if retained |

Template copies (for early migration or reference):

- `templates/workflows/node-ci.reusable.yml`
- `templates/workflows/python-ci.reusable.yml`
- `templates/workflows/code-quality.reusable.yml`

## Comparison

| Aspect | Copied templates | Reusable workflows |
|---|---|---|
| Migration speed | Fast | Slower (need to wire up) |
| Drift risk | High | Low |
| Customization | Full | Constrained by inputs |
| Update path | Manual re-copy | Automatic on ref update |
| Long-term viability | Low | High |

**Recommendation:** Use copied templates for the initial migration wave. Transition to reusable workflows once the standard stabilizes.

See also [`template-drift.md`](template-drift.md) for drift management and [`using-repo-standards.md`](using-repo-standards.md) for adoption commands.
