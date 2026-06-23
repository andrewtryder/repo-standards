# Existing repository migration

This guide walks through migrating an existing repository to the repo-standards blueprint.

## Philosophy

The first migration PR should be **focused and non-invasive**:

- Add standards infrastructure (workflows, governance files, AI/editor rules)
- Preserve existing deploy behavior
- Do not fix unrelated tech debt
- Do not change package managers or application code

Think of it as adding a safety net, not renovating the house.

For how documentation and AI/editor rules stay aligned, see [`ai-rules-maintenance.md`](ai-rules-maintenance.md).

## Step 1: Create a migration branch

```bash
git checkout main
git pull
git checkout -b chore/standards-migration
```

## Step 2: Detect likely profile

Before copying templates, run:

```bash
python3 /path/to/repo-standards/scripts/detect_repo_standard.py --repo .
```

The detector is read-only and advisory. Use its output to choose a starting profile, then review `.repo-policy.yml` manually. See [`detection.md`](detection.md).

If your repo deploys to Cloudflare, GCP, or Railway, read the matching deployment guide before migration:

- [`deployment/cloudflare.md`](deployment/cloudflare.md)
- [`deployment/gcp.md`](deployment/gcp.md)
- [`deployment/railway.md`](deployment/railway.md)

**Do not change deploy behavior during the first migration PR.**

### Optional: apply with the safe apply script

After detection, you can dry-run or apply standards infrastructure:

```bash
python3 /path/to/repo-standards/scripts/apply_repo_standards.py \
  --repo . \
  --standards /path/to/repo-standards \
  --mode existing \
  --workflow-strategy copied \
  --dry-run
```

Use `--apply` to write safe changes. The script skips existing files by default, never modifies deploy workflows, and writes `.repo-standards-migration-summary.md`.

Use `--analyze-existing` to inspect generated AI/editor outputs, deploy workflows, and coverage artifacts before applying. Use `--adoption-level` (`baseline`, `checks`, `reusable-ci`, `full`) and `--rules-strategy profile` for safer migrations. Use `--interactive` for confirmation prompts. See [`using-repo-standards.md`](using-repo-standards.md#one-command-apply) and [`github-models-migration.md`](github-models-migration.md).

The apply script adds `.editorconfig` when missing, warns (but does not create) a missing `LICENSE` when `.repo-policy.yml` declares an open-source license, and copies migration-friendly `docs-check.yml` / `secret-scan.yml` workflows.

## Step 3: Run the assessor (baseline)

Establish a baseline before making changes:

```bash
python3 /path/to/repo-standards/scripts/assess_repo_standards.py \
  --repo /path/to/your-repo \
  --standards /path/to/repo-standards \
  --base-ref main
```

Note the baseline score and warnings. You'll compare against this after migration.

## Step 4: Choose a profile

Review your project and choose the closest profile (use detector output from Step 2 as a starting point):

| Profile | Template | Typical use |
|---|---|---|
| `typescript-library` | `repo-policy.typescript-library.yml` | npm packages, shared libraries |
| `typescript-cloudflare-worker` | `repo-policy.typescript-cloudflare.yml` | Cloudflare Workers |
| `typescript-app` | `repo-policy.typescript-app.yml` | Frontend or backend apps |
| `python-service` | `repo-policy.python-service.yml` | Python services and APIs |
| `python-home-assistant` | `repo-policy.python-home-assistant.yml` | Home Assistant custom components |
| `mixed-special` | `repo-policy.mixed-special.yml` | Monorepos, multi-language, or unusual setups |

## Step 5: Add `.repo-policy.yml`

Copy the matching template:

```bash
cp /path/to/repo-standards/templates/repo-policy.<profile>.yml .repo-policy.yml
```

Customize:

- `name` — your project name
- `visibility` — `public` or `private`
- `license` — `MIT`, `proprietary`, or `none` (match your existing license)
- `commands` — match your existing scripts
- `quality_gates` — set coverage to `report-only` initially
- `deploy` — preserve your existing deploy workflow reference
- `governance` — set `contributing: required` and `pull_request_template: required`

## Step 6: Add `.nvmrc` (Node repos only)

```bash
cp /path/to/repo-standards/configs/node/.nvmrc .nvmrc
```

Edit to match your project's Node.js version. Check `package.json` `engines` field or existing CI configs.

## Step 7: Add Rulesync configuration

```bash
cp /path/to/repo-standards/templates/rulesync.jsonc .
mkdir -p .rulesync/rules
cp /path/to/repo-standards/ai/rules/*.md .rulesync/rules/
```

## Step 8: Generate AI/editor outputs

```bash
npx rulesync generate
```

This creates `AGENTS.md`, `.cursor/rules/*`, `.agents/rules/*`, and optionally `.agents/memories/*`.

## Step 9: Add governance files

### CONTRIBUTING.md

```bash
cp /path/to/repo-standards/templates/CONTRIBUTING.md .
```

Customize the project name and any existing contribution guidelines.

### LICENSE

Check if you already have a license. If not, or if you need to add one:

For public/open-source repos:

```bash
cp /path/to/repo-standards/templates/licenses/LICENSE-MIT.txt LICENSE
# Edit: replace [year] and [copyright holder]
```

For private/proprietary repos:

```bash
cp /path/to/repo-standards/templates/licenses/LICENSE-PROPRIETARY.txt LICENSE
```

**Important:** Do not change an existing license. Only add a license if one is missing, and choose the correct type for your repo's visibility.

### PR template

```bash
cp /path/to/repo-standards/templates/.github/PULL_REQUEST_TEMPLATE.md .github/PULL_REQUEST_TEMPLATE.md
```

(Only if `.github/` already exists; otherwise create it.)

## Step 10: Add non-invasive workflows

Add these workflows first — they don't change build or deploy behavior:

```bash
cp /path/to/repo-standards/templates/workflows/semantic-pull-request.yml .github/workflows/
cp /path/to/repo-standards/templates/workflows/ai-rules-check.yml .github/workflows/
cp /path/to/repo-standards/templates/workflows/docs-check.yml .github/workflows/
cp /path/to/repo-standards/templates/workflows/secret-scan.yml .github/workflows/
```

Add CI workflow only if you don't already have one, or if you want to replace it:

```bash
# Choose one:
cp /path/to/repo-standards/templates/workflows/node-ci.yml .github/workflows/ci.yml
# or
cp /path/to/repo-standards/templates/workflows/python-ci.yml .github/workflows/ci.yml
```

## Step 11: Add Dependabot

```bash
cp /path/to/repo-standards/templates/dependabot.yml .github/dependabot.yml
```

## Step 12: Update `.gitignore`

Ensure `coverage/` and other generated artifacts are ignored:

```bash
echo "" >> .gitignore
echo "# Coverage artifacts" >> .gitignore
echo "coverage/" >> .gitignore
echo "htmlcov/" >> .gitignore
echo ".coverage" >> .gitignore
```

If coverage files were previously tracked, remove them:

```bash
git rm -r --cached coverage/ 2>/dev/null || true
```

## Step 13: Preserve deploy behavior

**Do not modify deploy workflows in the first migration PR.** If your repo has existing deploy workflows (e.g., `.github/workflows/deploy.yml`), leave them untouched.

The first migration PR should only add standards infrastructure. Deploy changes should come in a follow-up PR after the standards are stable.

## Step 14: Run checks locally

```bash
# Node
npm run lint --if-present
npm run typecheck --if-present
npm test --if-present

# Python
ruff check .
pytest
```

## Step 15: Generate coverage and clean up

```bash
# Run coverage
npm run test:coverage --if-present
# or
coverage run -m pytest && coverage report

# Remove local coverage artifacts
rm -rf coverage/ .coverage htmlcov/
```

Stage any deletions of previously tracked coverage files:

```bash
git add -u  # stages deletions
```

## Step 16: Run the assessor again

```bash
python3 /path/to/repo-standards/scripts/assess_repo_standards.py \
  --repo /path/to/your-repo \
  --standards /path/to/repo-standards \
  --base-ref main \
  --run-safe-checks
```

Compare against your baseline. The score should be equal or higher. Resolve any new blockers.

## Step 17: Open a focused PR

```bash
git add .
git commit -m "chore(standards): adopt repo standards"
git push -u origin chore/standards-migration
```

PR title: `chore(standards): adopt repo standards`

In the PR description, note:
- What was added (workflows, governance files, AI/editor rules)
- What was preserved (deploy behavior, package manager)
- Any warnings that remain (low coverage, ESLint warnings, etc.)

## Recommended follow-up work

After the first migration PR merges:

1. Configure branch protection with required checks
2. Verify all CI workflows pass on main
3. Address warnings incrementally in follow-up PRs:
   - Fix ESLint warnings
   - Address npm audit findings
   - Improve test coverage
4. Consider transitioning from copied templates to reusable workflows
5. Normalize Release Please if the repo publishes releases
