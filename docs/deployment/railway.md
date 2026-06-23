# Railway deployment

Guidance for repositories deployed to Railway.

## Detection evidence

The detector recognizes Railway when it finds:

- `railway.json`
- `.github/workflows/*.yml` mentioning `railway`
- `README.md` mentioning Railway deploy instructions
- `Dockerfile` with Railway deploy documentation (secondary signal)

## Recommended profile

Railway projects are typically **`typescript-app`** or **`python-service`** depending on language. Railway does not have a dedicated profile.

```bash
python3 /path/to/repo-standards/scripts/detect_repo_standard.py --repo .
```

## What should remain repo-specific

Railway deployment should usually remain **repo-specific initially**:

- Railway project linking and service configuration
- Deploy triggers (GitHub integration vs CLI vs workflow)
- Environment variables configured in Railway dashboard
- `railway.json` build and deploy settings
- Custom Dockerfile or Nixpacks configuration

## What standards still apply

- `.repo-policy.yml` with the appropriate language profile
- AI/editor rules via Rulesync
- Semantic PR, AI rules check, docs check, secret scan workflows
- Dependabot
- CI workflows for lint, test, and build
- `.env.example` listing required variables (blank values only)

## First migration PR — do not change

- Do **not** change deploy behavior during first migration
- Do **not** modify `railway.json` for standards adoption
- Do **not** replace Railway-linked deploy workflows
- Do **not** commit Railway tokens or project secrets

## Secrets

Configure production secrets in the Railway dashboard or GitHub Actions secrets. Document required variable names in `.env.example` without real values.

## Suggested follow-up improvements

After the first migration PR merges:

1. Document Railway environments (staging, production) in `README.md`
2. List required Railway variables in `.env.example`
3. Reference the deploy workflow in `.repo-policy.yml` `deploy` section
4. Ensure CI validates the same build Railway deploys
5. Review whether deploy should move to reusable CI patterns later
