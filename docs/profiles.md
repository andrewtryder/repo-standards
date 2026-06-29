# Profiles

A **profile** is a named starting point for `.repo-policy.yml`. It encodes typical language/runtime, deploy assumptions, default commands, and quality gates.

Profiles also document dependency separation. Python pip profiles use
`requirements.txt` for runtime dependencies and `requirements-dev.txt` for
test/lint/coverage tooling. TypeScript profiles use package-manager-native
`devDependencies` for tooling and keep runtime `dependencies` focused on
production packages.

For how documentation and AI/editor rules stay aligned, see [`ai-rules-maintenance.md`](ai-rules-maintenance.md).
For file-pattern-aware tooling defaults, see [`code-quality-standards.md`](code-quality-standards.md).

## Available profiles

| Profile | Typical use | Language/runtime | Deploy assumption |
|---|---|---|---|
| `typescript-library` | npm packages/shared libraries | Node/TypeScript | npm publish or no deploy |
| `typescript-cloudflare-worker` | Cloudflare Workers | Node/TypeScript | Cloudflare/Wrangler |
| `typescript-app` | Frontend or backend apps | Node/TypeScript | Repo-specific |
| `python-service` | APIs/services/scripts | Python | Repo-specific |
| `python-home-assistant` | Home Assistant custom components | Python | Home Assistant ecosystem |
| `mixed-special` | Monorepos/unusual repos | Mixed | Manual review |

## Profile templates

| Profile | Template file |
|---|---|
| `typescript-library` | `templates/repo-policy.typescript-library.yml` |
| `typescript-cloudflare-worker` | `templates/repo-policy.typescript-cloudflare.yml` |
| `typescript-app` | `templates/repo-policy.typescript-app.yml` |
| `python-service` | `templates/repo-policy.python-service.yml` |
| `python-home-assistant` | `templates/repo-policy.python-home-assistant.yml` |
| `mixed-special` | `templates/repo-policy.mixed-special.yml` |

## How to choose a profile

1. **Run the detector** (advisory):

   ```bash
   python3 /path/to/repo-standards/scripts/detect_repo_standard.py --repo .
   ```

2. **Review the recommendation** against your project's actual structure and deploy path.

3. **Copy the matching template** and customize `.repo-policy.yml`.

4. **Set deploy behavior** to match your existing workflow — especially for existing repos. Do not change deploy behavior in the first migration PR.

### Decision guide

- **Publishing an npm package?** → `typescript-library`
- **Cloudflare Worker with Wrangler?** → `typescript-cloudflare-worker`
- **Node app (frontend, API, CLI) without npm publish?** → `typescript-app`
- **Python API, service, or script?** → `python-service`
- **Home Assistant custom component?** → `python-home-assistant`
- **Monorepo, multi-language, or unusual setup?** → `mixed-special`

`mixed-special` repos should migrate conservatively — start with non-invasive workflows and governance files, then adopt CI quality gates incrementally.

Profiles determine applicability; file patterns determine which language and format checks run.
For example, a mixed repo may use one profile while still running ShellCheck only when shell files
exist and actionlint only when GitHub Actions workflows exist.

## Detection vs adoption

| State | Meaning |
|---|---|
| **Detected** | What the read-only detector infers from repo files |
| **Recommended** | Starting profile the detector suggests |
| **Adopted** | What `.repo-policy.yml` declares after human review |

The detector recommends; `.repo-policy.yml` is authoritative once adopted. See [`detection.md`](detection.md).

## Deploy provider guidance

Deploy behavior varies by provider. During first migration, preserve existing deploy workflows:

| Provider | Guidance |
|---|---|
| Cloudflare | [`deployment/cloudflare.md`](deployment/cloudflare.md) |
| GCP | [`deployment/gcp.md`](deployment/gcp.md) |
| Railway | [`deployment/railway.md`](deployment/railway.md) |
| None | No external deploy — profile deploy section may be minimal |
