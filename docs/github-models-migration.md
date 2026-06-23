# GitHub Models migration assessment

Optional GitHub Models advisory assessment helps classify migration risks for existing repositories.

## Policy

- AI assessment is advisory only.
- It never applies changes directly.
- It is useful for classifying ambiguous workflows and migration risks.
- Deterministic detection and the apply script remain authoritative for file actions.

## Token

Create a token with `models: read` permission:

```bash
export GITHUB_TOKEN=...
```

Do not commit `.env`.

## Dry-run safe summary

```bash
python3 scripts/apply_repo_standards.py \
  --repo . \
  --standards . \
  --mode existing \
  --analyze-existing \
  --dry-run-ai-summary
```

## Live advisory assessment

```bash
python3 scripts/apply_repo_standards.py \
  --repo . \
  --standards . \
  --mode existing \
  --analyze-existing \
  --ai-assessment \
  --model openai/gpt-4o-mini
```

## Related docs

- [`using-repo-standards.md`](using-repo-standards.md) — migration flows
- [`github-models-detection.md`](github-models-detection.md) — profile detection advisor
