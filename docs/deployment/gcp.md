# GCP deployment

Guidance for repositories deployed to Google Cloud Platform.

## Detection evidence

The detector recognizes GCP when it finds:

- `cloudbuild.yaml` or `cloudbuild.yml`
- `app.yaml` (App Engine)
- `Dockerfile` plus a workflow using `gcloud`
- `.github/workflows/*.yml` mentioning:
  - `gcloud`
  - `google-github-actions`
  - `cloud run`
  - `cloud functions`
  - `app engine`
  - `artifact registry`
  - `workload identity`

## Recommended profile

GCP projects are typically **`python-service`** or **`typescript-app`** depending on language. The detector recommends based on language evidence, not GCP-specific profiles.

```bash
python3 /path/to/repo-standards/scripts/detect_repo_standard.py --repo .
```

## What should remain repo-specific

GCP deployment should usually be **repo-specific initially**:

- Cloud Build configuration (`cloudbuild.yaml`)
- Cloud Run / Cloud Functions / App Engine service definitions
- Artifact Registry image names and tags
- Workload Identity Federation or service account setup
- Environment-specific deploy workflows and approval gates
- Infrastructure-as-code (Terraform, Pulumi) if present

This standards repo does not ship full GCP deployment templates. Detect and document the deploy path; do not replace it during first migration.

## What standards still apply

- `.repo-policy.yml` with the appropriate language profile
- AI/editor rules via Rulesync
- Semantic PR, AI rules check, docs check, secret scan workflows
- Dependabot
- CI workflows for lint, test, and build (separate from deploy)
- `.env.example` documenting non-secret configuration only

## First migration PR — do not change

- Do **not** replace Cloud Build or `gcloud` deploy workflows
- Do **not** change service account permissions or WIF configuration
- Do **not** modify `cloudbuild.yaml` for standards adoption
- Do **not** commit GCP service account keys or JSON key files

## Secrets

Store secrets in:

- GitHub Actions environments and secrets
- GCP Secret Manager
- Workload Identity Federation (preferred over long-lived keys)

Never commit service account JSON keys to the repository.

## Suggested follow-up improvements

After the first migration PR merges:

1. Document the deploy path in `README.md` (Cloud Run vs Functions vs App Engine)
2. Add deploy workflow to `.repo-policy.yml` `deploy` section as reference-only
3. Ensure CI builds the same artifact the deploy workflow uses
4. Review IAM least-privilege for CI deploy roles
5. Consider pinning `google-github-actions/*` versions in workflows
