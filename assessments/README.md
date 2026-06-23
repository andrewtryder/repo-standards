# Assessments

This directory separates committed reference examples from local generated assessor output.

## Layout

| Path | Purpose |
|---|---|
| `assessments/examples/` | Committed sanitized reference outputs |
| `assessments/generated/` | Local generated outputs (gitignored except `.gitkeep`) |

## Reference examples

The committed `examples/nab-api/` files are sanitized examples from the nab-api pilot migration. They show how assessor output evolves across v1, v2, and v3 scoring logic.

## Regenerating assessments

Run the assessor against an application repository:

```bash
python3 scripts/assess_repo_standards.py \
  --repo /path/to/application-repo \
  --standards /path/to/repo-standards \
  --base-ref main \
  --run-safe-checks
```

By default, reports are written to `assessments/generated/` as:

```txt
{repo-name}.standards-assessment-v3.md
{repo-name}.standards-assessment-v3.json
```

Use `--output-dir` to write reports elsewhere.

## Gitignore policy

New assessor runs write generated `.md` and `.json` files to `assessments/generated/` by default. Those outputs are gitignored. Committed reference examples under `assessments/examples/` remain tracked.
