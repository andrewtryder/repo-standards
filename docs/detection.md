# Detection

The repo standard **detector** recommends a starting profile and relevant templates for a target repository. It is read-only and advisory.

## Principles

Detection is:

- **read-only** — never modifies the target repository
- **advisory** — recommends; does not enforce
- **evidence-based** — lists files and content matches that drove the recommendation
- **conservative** — prefers `mixed-special` when uncertain
- **intended to recommend** a starting profile and relevant modules

Once a project adopts the standard, `.repo-policy.yml` is the source of truth.

## Usage

```bash
python3 /path/to/repo-standards/scripts/detect_repo_standard.py --repo /path/to/project
python3 /path/to/repo-standards/scripts/detect_repo_standard.py --repo /path/to/project --format json
python3 /path/to/repo-standards/scripts/detect_repo_standard.py --repo /path/to/project --format markdown
```

Markdown is the default output format.

## What it detects

| Field | Possible values |
|---|---|
| `language` | `typescript`, `python`, `mixed`, `unknown` |
| `package_manager` | `npm`, `pnpm`, `yarn`, `bun`, `pip-requirements`, `uv`, `poetry`, `unknown` |
| `deployment_provider` | `cloudflare`, `gcp`, `railway`, `none`, `unknown` |
| `recommended_profile` | See [`profiles.md`](profiles.md) |

## Example JSON output

```json
{
  "language": "typescript",
  "package_manager": "npm",
  "deployment_provider": "cloudflare",
  "recommended_profile": "typescript-cloudflare-worker",
  "confidence": 0.92,
  "evidence": [
    "package.json exists",
    "wrangler.toml exists",
    ".github/workflows/deploy.yml mentions wrangler"
  ],
  "recommended_templates": [
    "templates/repo-policy.typescript-cloudflare.yml",
    "templates/rulesync.jsonc",
    "ai/rules/*",
    "templates/workflows/semantic-pull-request.yml",
    "templates/workflows/ai-rules-check.yml",
    "templates/workflows/docs-check.yml",
    "templates/workflows/secret-scan.yml",
    "templates/dependabot.yml"
  ],
  "manual_review": [
    "Verify deploy workflow should remain repo-specific"
  ]
}
```

## Detected vs recommended vs adopted

| Concept | Description |
|---|---|
| **Detected state** | What the script infers from files (language, package manager, deploy provider) |
| **Recommended profile** | Starting profile based on detection rules in `profiles/detection.yml` |
| **Adopted `.repo-policy.yml`** | What the repo owner sets after review — authoritative |

The detector may recommend `typescript-cloudflare-worker`, but the owner may choose `typescript-app` if the project is transitioning away from Workers. That is fine — update `.repo-policy.yml` accordingly.

## Detection rules

Declarative rules live in [`profiles/detection.yml`](../profiles/detection.yml). The script loads this file when PyYAML is available; otherwise it uses built-in defaults.

## Manual review notes

The detector may flag items requiring human judgment:

- Unusual monorepo layouts
- Multiple deploy providers detected
- Could not confidently detect language/profile
- Deploy workflow should remain repo-specific during first migration

Always review `.repo-policy.yml` before adopting the standard.

## Related docs

- [`profiles.md`](profiles.md) — profile descriptions
- [`deployment/cloudflare.md`](deployment/cloudflare.md) — Cloudflare-specific guidance
- [`deployment/gcp.md`](deployment/gcp.md) — GCP-specific guidance
- [`deployment/railway.md`](deployment/railway.md) — Railway-specific guidance
- [`new-repository-setup.md`](new-repository-setup.md) — setup after detection
- [`existing-repository-migration.md`](existing-repository-migration.md) — migration with detection
