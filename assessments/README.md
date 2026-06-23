# Assessments

This directory holds reference assessment outputs from pilot migrations and the default output location for new assessor runs.

## Reference examples

The committed `nab-api.*` files are sanitized examples from the nab-api pilot migration. They show how assessor output evolves across v1, v2, and v3 scoring logic.

## Regenerating assessments

Run the v3 assessor against an application repository:

```bash
python3 scripts/assess_repo_standards_migration_v3.py \
  --repo /path/to/application-repo \
  --standards /path/to/repo-standards \
  --base-ref main \
  --run-safe-checks
```

By default, reports are written here as:

```txt
{repo-name}.standards-assessment-v3.md
{repo-name}.standards-assessment-v3.json
```

Use `--output-dir` to write reports elsewhere.

## Gitignore policy

New assessor runs write generated `.md` and `.json` files to this directory by default. Those outputs are gitignored. Only this README and the committed reference examples are tracked.
