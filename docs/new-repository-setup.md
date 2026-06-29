# New repository setup

This guide walks through setting up a brand-new repository using the repo-standards blueprint.

For how documentation and AI/editor rules stay aligned, see [`ai-rules-maintenance.md`](ai-rules-maintenance.md).

## Prerequisites

- A GitHub account
- Node.js (for Node/TypeScript repos) or Python (for Python repos) installed locally
- `npx` available (comes with npm)

## Step 1: Create the repository

```bash
mkdir my-new-project
cd my-new-project
git init
```

Create the repository on GitHub and push:

```bash
git remote add origin https://github.com/<user>/<repo>.git
```

## Step 2: Choose a profile

See [`profiles.md`](profiles.md) for full profile descriptions.

### Optional: detect profile from an existing local project shape

If the repository already has starter files, run:

```bash
python3 /path/to/repo-standards/scripts/detect_repo_standard.py --repo .
```

Use the recommendation as a starting point, then create `.repo-policy.yml`. Detection is read-only and advisory — see [`detection.md`](detection.md).

Select the profile that best matches your project:

| Profile | Template | Use case |
|---|---|---|
| `typescript-library` | `repo-policy.typescript-library.yml` | npm packages, shared libraries |
| `typescript-cloudflare-worker` | `repo-policy.typescript-cloudflare.yml` | Cloudflare Workers |
| `typescript-app` | `repo-policy.typescript-app.yml` | Frontend or backend apps |
| `python-service` | `repo-policy.python-service.yml` | Python services and APIs |
| `python-home-assistant` | `repo-policy.python-home-assistant.yml` | Home Assistant custom components |
| `mixed-special` | `repo-policy.mixed-special.yml` | Monorepos, multi-language, or unusual setups |

## Step 3: Add `.repo-policy.yml`

Copy the matching template and customize:

```bash
cp /path/to/repo-standards/templates/repo-policy.typescript-library.yml .repo-policy.yml
```

Edit `.repo-policy.yml` to set:

- `name` — your project name
- `visibility` — `public` or `private`
- `license` — `MIT`, `proprietary`, or `none`
- The correct `commands` for your project
- The correct `quality_gates`

For new Python pip repositories, add `requirements-dev.txt` for development and
test tools such as pytest, coverage, and Ruff. For JavaScript/TypeScript
repositories, put tooling packages in `devDependencies`, not runtime
`dependencies`.

## Step 4: Add `.nvmrc` (Node repos only)

```bash
cp /path/to/repo-standards/configs/node/.nvmrc .nvmrc
```

Edit `.nvmrc` to specify your project's Node.js version (e.g., `24`).

## Step 5: Add Rulesync configuration

Rulesync is required for all repositories. If this is not a Node/TypeScript
project, add a private tooling-only `package.json` and pin Rulesync there; this
does not make the application a JavaScript project.

```bash
cp /path/to/repo-standards/templates/rulesync.jsonc .
mkdir -p .rulesync/rules
cp /path/to/repo-standards/ai/rules/*.md .rulesync/rules/
npm install -D rulesync
```

Customize the rules files for your project. At minimum, review:

- `.rulesync/rules/00-org.md`** — organization-wide rules (usually no changes needed)
- `.rulesync/rules/10-typescript.md`** or `20-python.md`** — language-specific rules

## Step 6: Generate AI/editor outputs

```bash
npx rulesync generate
```

This creates:

- `AGENTS.md`
- `.cursor/rules/*.mdc`
- `.agents/rules/*.md`
- `.agents/memories/*.md` (if `antigravity-ide` target is enabled)

Verify:

```bash
find AGENTS.md .cursor .agents .rulesync -maxdepth 4 -type f -print | sort
```

## Step 7: Add governance files

### CONTRIBUTING.md

```bash
cp /path/to/repo-standards/templates/CONTRIBUTING.md .
```

Customize the project name and any repo-specific contribution guidelines.

### LICENSE

For public/open-source MIT repos, use the apply script with `--add-license`:

```bash
python3 /path/to/repo-standards/scripts/apply_repo_standards.py \
  --repo . \
  --standards /path/to/repo-standards \
  --mode new \
  --visibility public \
  --license MIT \
  --add-license \
  --apply
```

Or copy manually:

```bash
cp /path/to/repo-standards/LICENSE LICENSE
# Edit: replace copyright holder and year
```

For private/proprietary repos:

```bash
cp /path/to/repo-standards/templates/licenses/LICENSE-PROPRIETARY.txt LICENSE
```

### PR template

```bash
mkdir -p .github
cp /path/to/repo-standards/templates/.github/PULL_REQUEST_TEMPLATE.md .github/
```

## Step 8: Add GitHub Actions workflows

```bash
mkdir -p .github/workflows
```

Copy the workflows you need:

```bash
# Always recommended:
cp /path/to/repo-standards/templates/workflows/semantic-pull-request.yml .github/workflows/
cp /path/to/repo-standards/templates/workflows/ai-rules-check.yml .github/workflows/
cp /path/to/repo-standards/templates/workflows/docs-check.yml .github/workflows/
cp /path/to/repo-standards/templates/workflows/secret-scan.yml .github/workflows/

# CI (choose based on profile):
cp /path/to/repo-standards/templates/workflows/node-ci.yml .github/workflows/ci.yml
# or
cp /path/to/repo-standards/templates/workflows/python-ci.yml .github/workflows/ci.yml

# Release Please (if applicable):
cp /path/to/repo-standards/templates/workflows/release-please.simple.yml .github/workflows/release-please.yml
```

The AI rules check workflow uses `.nvmrc` when present and falls back to Node 24 for non-Node repositories (for example Python repos that still use Rulesync).

## Step 9: Add Dependabot

```bash
cp /path/to/repo-standards/templates/dependabot.yml .github/dependabot.yml
```

Customize for monorepos by adding additional directory entries.

## Step 10: Add tool configs

For Node repos:

```bash
cp /path/to/repo-standards/configs/node/commitlint.config.mjs .  # optional
```

For Python repos:

```bash
cp /path/to/repo-standards/configs/python/.pre-commit-config.yaml .
cp /path/to/repo-standards/configs/python/ruff.toml .
```

## Step 11: Update `.gitignore`

Ensure your `.gitignore` includes:

```txt
# Build and coverage artifacts
coverage/
htmlcov/
.coverage
node_modules/
dist/
*.env
*.pem
id_rsa
```

## Step 12: Run checks

```bash
# Node
npm install
npm run lint --if-present
npm run typecheck --if-present
npm test --if-present

# Python
pip install -r requirements.txt -r requirements-dev.txt
ruff check .
ruff format --check .
pytest
```

## Step 13: Run the assessor

```bash
python3 /path/to/repo-standards/scripts/assess_repo_standards.py \
  --repo /path/to/my-new-project \
  --standards /path/to/repo-standards \
  --run-safe-checks
```

## Step 14: Initial commit

```bash
git add .
git commit -m "chore(standards): initialize repository standards"
git push -u origin main
```

## Recommended next steps

1. Configure branch protection rules (see `docs/branch-protection.md`)
2. Verify all CI workflows pass on the first push
3. Create a test PR to validate the semantic PR and docs checks
4. Review and customize the generated AI/editor rules for your project
