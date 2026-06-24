# GitHub Models-assisted detection

GitHub Models-assisted detection is an optional advisory layer on top of deterministic repo detection.

## Policy

- Deterministic detection is default.
- GitHub Models is optional.
- Model output is advisory.
- `.repo-policy.yml` remains authoritative.
- The model-assisted script is read-only.
- No secrets or full source files should be sent to the model.

## Token

Create a token with `models: read` permission and set:

```bash
export GITHUB_TOKEN=...
```

For local experimentation, a `.env` file may contain:

```env
GITHUB_TOKEN=...
```

Do not commit `.env`.

## Dry run

```bash
python3 scripts/model_assisted_repo_detection.py \
  --repo . \
  --standards . \
  --dry-run-summary \
  --format json
```

## Live model call

```bash
python3 scripts/model_assisted_repo_detection.py \
  --repo . \
  --standards . \
  --model openai/gpt-4o-mini \
  --format markdown
```

Optional local live test when a token is available:

```bash
if [ -n "${GITHUB_TOKEN:-}" ]; then
  python3 scripts/model_assisted_repo_detection.py \
    --repo . \
    --standards . \
    --model openai/gpt-4o-mini \
    --format markdown
fi
```

## When to use

Use model-assisted detection when:

- deterministic detection returns `mixed-special`
- multiple deploy providers are detected
- app vs library classification is unclear
- deployment provider is mentioned but not clearly active
- human review needs better explanation

## When not to use

Do not use model-assisted detection to:

- modify `.repo-policy.yml`
- change workflows
- approve compliance
- replace the assessor
- send source code or secrets to a model

## Related docs

- [`detection.md`](detection.md) — deterministic detection
- [`using-repo-standards.md`](using-repo-standards.md) — adoption workflows
