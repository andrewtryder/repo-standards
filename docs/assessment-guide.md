# Assessment guide

The repo-standards assessor scores a repository's alignment with **Repo Standard v1.3**. Use `assess_repo_standards_migration_v3.py` as the current assessor. This guide explains how to run it and interpret results.

For **profile detection** before migration, use the read-only detector instead:

```bash
python3 /path/to/repo-standards/scripts/detect_repo_standard.py --repo /path/to/application-repo
```

See [`detection.md`](detection.md) for detection vs assessment differences.

## Running the assessor

### Basic usage

```bash
python3 /path/to/repo-standards/scripts/assess_repo_standards_migration_v3.py \
  --repo /path/to/application-repo \
  --standards /path/to/repo-standards \
  --base-ref main \
  --run-safe-checks
```

### Arguments

| Argument | Required | Description |
|---|---|---|
| `--repo` | Yes | Path to the application repository |
| `--standards` | Yes | Path to the repo-standards repository |
| `--base-ref` | No | Git ref to compare against (default: `main`) |
| `--run-safe-checks` | No | Runs commands in the target repo (install, lint, tests, etc.) |
| `--output-dir` | No | Custom output directory for assessment reports |

### Read-only mode (no `--run-safe-checks`)

Checks file existence, workflow configuration, and `.repo-policy.yml` structure without executing any commands. Safe to run against any repo.

```bash
python3 assess_repo_standards_migration_v3.py \
  --repo /path/to/repo \
  --standards /path/to/repo-standards \
  --base-ref main
```

### Full mode (with `--run-safe-checks`)

Runs safe verification commands in the target repo:

- `npm ci` / `pip install` (install dependencies)
- `npm run lint` / `ruff check .` (lint)
- `npm run typecheck` / (nothing for Python, by default)
- `npm test` / `pytest` (tests)
- `npm run test:coverage` / `coverage run -m pytest` (coverage)
- `npm run build` / (nothing for Python, by default)
- `npx rulesync generate` (AI rules drift check)
- `git diff --check` (whitespace)

All commands use `--if-present` where applicable. If a script doesn't exist, that step is skipped.

## Output

The assessor produces two files in `assessments/` (or `--output-dir`):

- `<repo>.standards-assessment-v3.md` — human-readable report
- `<repo>.standards-assessment-v3.json` — machine-readable JSON

### Score

The score ranges from 0 to 100. Typical interpretations:

| Score | Meaning |
|---|---|
| 90–100 | Ready for review. Remaining items are warnings or follow-up work. |
| 75–89 | Mostly aligned. Review warnings before merging. |
| 0–74 | Partially aligned. Revise before review. |

### Verdict

One of:

- "Not ready to merge. Clean up blockers first."
- "Looks ready for review. Remaining items are warnings or follow-up work."
- "Mostly aligned, but review warnings before merging."
- "Partially aligned. Revise before review."

## Blockers vs warnings

### Blockers (must fix)

Blockers indicate issues that make the repo unsafe or non-compliant:

- Missing `.repo-policy.yml`
- Missing `.rulesync/rules/*`
- Missing generated AI/editor files (`AGENTS.md`, `.cursor/rules/*.mdc`, `.agents/rules/*.md`)
- Added/modified generated coverage artifacts (`A coverage/...` or `M coverage/...`)
- Secret-like files in the diff
- Risky deploy changes in a standards-only PR
- Failed safe verification commands

### Warnings (follow-up work)

Warnings indicate technical debt or recommended improvements that don't block the current PR:

- Deleted generated coverage artifacts (`D coverage/...` when `coverage/` is in `.gitignore`)
- Low test coverage
- ESLint warnings or errors
- npm audit vulnerabilities
- Legacy stale agent files being removed
- Missing `rulesync` devDependency (acceptable initially)
- Missing `.nvmrc` in a Node repo
- Missing `.github/dependabot.yml`
- Missing secret scanning workflow

## When to run the assessor

- **Before migration**: Establish a baseline score. Understand what needs to change.
- **During migration**: Verify incremental progress.
- **After migration**: Confirm all blockers are resolved.
- **Periodically**: Check for drift after repo-standards updates.

## Interpreting specific warnings

### "Deleted coverage artifacts detected"

This is acceptable cleanup. It means `coverage/` was previously tracked in git but is now properly ignored. No action needed unless `.gitignore` is missing the `coverage/` entry.

### "Low coverage"

Keep coverage as report-only. Do not add thresholds until coverage is improved. Track as tech debt.

### "ESLint passed but reported N warnings"

Track existing warnings as technical debt. Do not fix them in the standards PR unless trivial.

### "npm audit reported N vulnerabilities"

Open a separate dependency-audit PR. Do not mix audit fixes into the standards PR.

### "Missing `.nvmrc`"

Recommended for Node repos. Add a root `.nvmrc` with the project's Node.js version. Not yet a blocker.

### "Missing `.github/dependabot.yml`"

Recommended. Copy from `templates/dependabot.yml`. Not yet a blocker.

### "Missing secret scanning workflow"

Recommended. Copy from `templates/workflows/secret-scan.yml`. Not yet a blocker.

## Exit code

The assessor exits with:

- `0` — no blockers (warnings may exist)
- `1` — one or more blockers detected

This makes it suitable for use in CI:

```bash
# In a workflow or pre-commit hook:
python3 assess_repo_standards_migration_v3.py \
  --repo . \
  --standards /path/to/repo-standards \
  --base-ref main \
  --run-safe-checks
```
