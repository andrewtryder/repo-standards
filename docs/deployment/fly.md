# Fly.io deployment

Guidance for repositories deployed to Fly.io.

## Detection signals

Repo Standards treats these as Fly deployment signals:

- `fly.toml`
- `.github/workflows/*.yml` or `.github/workflows/*.yaml` mentioning `flyctl`, `fly.io`, or `fly deploy`
- `README.md` mentioning Fly deployment instructions

## Migration posture

Fly deployment should remain **repo-specific initially**:

- Preserve `fly.toml`
- Preserve existing `flyctl deploy` workflows
- Add Repo Standards CI and governance checks alongside deploy workflows
- Do not change Fly app names, regions, machines, secrets, volumes, or deploy triggers during standards adoption

## Recommended policy

Use the language profile that matches the application, then set deploy metadata to Fly:

```yaml
deploy:
  provider: fly
  workflow: repo-specific
```

## Follow-up hardening

After the standards migration is green:

1. Document Fly deploy and rollback behavior in `README.md`.
2. Confirm `FLY_API_TOKEN` is stored as a GitHub Actions secret.
3. Ensure CI validates the same code path that Fly deploys.
4. Consider whether release automation should publish before deploy.
