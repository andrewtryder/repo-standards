# Using repo-standards

This guide explains how to apply repo-standards to a repository.

Use it when you want a practical adoption path with commands, generated plans, and agent-friendly steps.

## Choose your path

| Situation | Start here |
|---|---|
| Brand-new repository | [New repository flow](#new-repository-flow) |
| Existing repository | [Existing repository migration flow](#existing-repository-migration-flow) |
| Unsure what applies | [Run the detector](#quick-command-flow) |
| Want less workflow drift | [Reusable workflows](#reusable-workflows) |
| Want an AI agent to help | [Agent-assisted adoption](#agent-assisted-adoption) |

## Core rule

`.repo-policy.yml` is authoritative after adoption.

Detection recommends. Humans review. The adopted repo policy decides.

## Safety rule for existing repos

The first standards migration PR should be non-invasive:

- add standards infrastructure
- preserve existing deploy behavior
- do not change package managers
- do not refactor application code
- do not fix unrelated lint/audit/coverage debt

## Quick command flow

Set the path to your local clone of repo-standards:

```bash
export REPO_STANDARDS=/path/to/repo-standards
```

Run detection:

```bash
python3 "$REPO_STANDARDS/scripts/detect_repo_standard.py" --repo . --format markdown
```

Generate a baseline assessment:

```bash
python3 "$REPO_STANDARDS/scripts/assess_repo_standards.py" \
  --repo . \
  --standards "$REPO_STANDARDS" \
  --base-ref main
```

Create a migration branch:

```bash
git checkout main
git pull
git checkout -b chore/standards-migration
```

After applying standards, run:

```bash
python3 "$REPO_STANDARDS/scripts/assess_repo_standards.py" \
  --repo . \
  --standards "$REPO_STANDARDS" \
  --base-ref main \
  --run-safe-checks
```

### Optional: generate an adoption plan

The read-only planner prints recommended commands without modifying the target repo:

```bash
python3 "$REPO_STANDARDS/scripts/plan_repo_standards_adoption.py" \
  --repo . \
  --standards "$REPO_STANDARDS" \
  --mode existing \
  --format markdown
```

Use `--mode new` for a brand-new repository. Use `--format shell` for a commented shell script.

## One-command apply

### Analyze

```bash
python3 "$REPO_STANDARDS/scripts/apply_repo_standards.py" \
  --repo . \
  --standards "$REPO_STANDARDS" \
  --mode existing \
  --analyze-existing
```

### Interactive migration

```bash
python3 "$REPO_STANDARDS/scripts/apply_repo_standards.py" \
  --repo . \
  --standards "$REPO_STANDARDS" \
  --mode existing \
  --adoption-level checks \
  --workflow-strategy copied \
  --rules-strategy profile \
  --interactive
```

### Non-interactive safe apply

```bash
python3 "$REPO_STANDARDS/scripts/apply_repo_standards.py" \
  --repo . \
  --standards "$REPO_STANDARDS" \
  --mode existing \
  --adoption-level baseline \
  --workflow-strategy copied \
  --rules-strategy profile \
  --apply
```

### Full migration with existing generated rule migration and coverage cleanup

```bash
python3 "$REPO_STANDARDS/scripts/apply_repo_standards.py" \
  --repo . \
  --standards "$REPO_STANDARDS" \
  --mode existing \
  --adoption-level full \
  --workflow-strategy copied \
  --rules-strategy profile \
  --apply \
  --migrate-existing-agent-rules \
  --cleanup-generated-artifacts \
  --run-assessment
```

### Optional AI advisory assessment

```bash
python3 "$REPO_STANDARDS/scripts/apply_repo_standards.py" \
  --repo . \
  --standards "$REPO_STANDARDS" \
  --mode existing \
  --analyze-existing \
  --ai-assessment \
  --model openai/gpt-4o-mini
```

See [`github-models-migration.md`](github-models-migration.md). AI assessment is advisory and never applies changes directly.

The apply script does not change deploy workflows, release workflows, package manager files, or application source. Review `.repo-policy.yml` after apply.

Use `--allow-generated-output-rewrite` when you accept Rulesync deleting existing generated agent/editor files. Use `--migrate-existing-agent-rules` to copy repo-specific generated rules into `.rulesync/rules/` first.

## New repository flow

```bash
mkdir my-new-project
cd my-new-project
git init

export REPO_STANDARDS=/path/to/repo-standards

python3 "$REPO_STANDARDS/scripts/detect_repo_standard.py" --repo . --format markdown
```

Copy standards infrastructure after reviewing the detected profile:

```bash
# Example: choose the right profile template after detection
cp "$REPO_STANDARDS/templates/repo-policy.typescript-app.yml" .repo-policy.yml

# Rulesync source
cp "$REPO_STANDARDS/templates/rulesync.jsonc" .
mkdir -p .rulesync/rules
cp "$REPO_STANDARDS/ai/rules/"*.md .rulesync/rules/

# Governance
cp "$REPO_STANDARDS/templates/CONTRIBUTING.md" .
mkdir -p .github
cp "$REPO_STANDARDS/templates/.github/PULL_REQUEST_TEMPLATE.md" .github/PULL_REQUEST_TEMPLATE.md

# Workflows
mkdir -p .github/workflows
cp "$REPO_STANDARDS/templates/workflows/semantic-pull-request.yml" .github/workflows/
cp "$REPO_STANDARDS/templates/workflows/ai-rules-check.yml" .github/workflows/
cp "$REPO_STANDARDS/templates/workflows/docs-check.yml" .github/workflows/
cp "$REPO_STANDARDS/templates/workflows/secret-scan.yml" .github/workflows/

# Dependabot
cp "$REPO_STANDARDS/templates/dependabot.yml" .github/dependabot.yml
```

Node repos should copy `.nvmrc`:

```bash
cp "$REPO_STANDARDS/configs/node/.nvmrc" .nvmrc
```

Rulesync generation creates generated AI/editor outputs:

```bash
npx rulesync generate
```

Run the assessor:

```bash
python3 "$REPO_STANDARDS/scripts/assess_repo_standards.py" \
  --repo . \
  --standards "$REPO_STANDARDS" \
  --run-safe-checks
```

For full detail, see [`new-repository-setup.md`](new-repository-setup.md).

## Existing repository migration flow

```bash
export REPO_STANDARDS=/path/to/repo-standards

git checkout main
git pull
git checkout -b chore/standards-migration
```

Detection:

```bash
python3 "$REPO_STANDARDS/scripts/detect_repo_standard.py" --repo . --format markdown
```

Baseline assessment:

```bash
python3 "$REPO_STANDARDS/scripts/assess_repo_standards.py" \
  --repo . \
  --standards "$REPO_STANDARDS" \
  --base-ref main
```

Copy only standards infrastructure after reviewing the profile:

```bash
cp "$REPO_STANDARDS/templates/repo-policy.<profile>.yml" .repo-policy.yml

cp "$REPO_STANDARDS/templates/rulesync.jsonc" .
mkdir -p .rulesync/rules
cp "$REPO_STANDARDS/ai/rules/"*.md .rulesync/rules/

mkdir -p .github/workflows
cp "$REPO_STANDARDS/templates/workflows/semantic-pull-request.yml" .github/workflows/
cp "$REPO_STANDARDS/templates/workflows/ai-rules-check.yml" .github/workflows/
cp "$REPO_STANDARDS/templates/workflows/docs-check.yml" .github/workflows/
cp "$REPO_STANDARDS/templates/workflows/secret-scan.yml" .github/workflows/
```

Do not replace existing deploy workflows in the first migration PR.

Do not change package managers.

Do not refactor application code.

Do not fix unrelated lint/audit/coverage debt in the standards PR.

Cleanup commands:

```bash
# Ignore generated coverage artifacts
{
  echo ""
  echo "# Coverage artifacts"
  echo "coverage/"
  echo "htmlcov/"
  echo ".coverage"
} >> .gitignore

# If coverage was previously tracked, remove it from the index
git rm -r --cached coverage/ 2>/dev/null || true
```

Generate AI/editor outputs:

```bash
npx rulesync generate
```

Run final assessment:

```bash
python3 "$REPO_STANDARDS/scripts/assess_repo_standards.py" \
  --repo . \
  --standards "$REPO_STANDARDS" \
  --base-ref main \
  --run-safe-checks
```

Open PR:

```bash
git add .
git commit -m "chore(standards): adopt repo standards"
git push -u origin chore/standards-migration
```

For full detail, see [`existing-repository-migration.md`](existing-repository-migration.md).

## Reusable workflows

Copied workflows are easiest for first adoption. Reusable workflows are preferred long-term because they reduce drift.

Live reusable workflows are:

- `.github/workflows/node-ci.reusable.yml`
- `.github/workflows/python-ci.reusable.yml`

Stable consumers should pin to a release tag such as `@v1.3.0`.

Use `@main` only for canary repos that intentionally track unreleased changes.

Node caller example:

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  node-ci:
    uses: andrewtryder/repo-standards/.github/workflows/node-ci.reusable.yml@v1.3.0
    with:
      node_version: "24"
      install_command: "npm ci"
      format_check_command: "npm run format:check"
      lint_command: "npm run lint"
      typecheck_command: "npm run typecheck"
      test_command: "npm test"
      coverage_command: "npm run test:coverage"
      build_command: "npm run build"
```

Python caller example:

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  python-ci:
    uses: andrewtryder/repo-standards/.github/workflows/python-ci.reusable.yml@v1.3.0
    with:
      python_version: "3.12"
      install_command: "python -m pip install -r requirements.txt -r requirements-dev.txt"
      format_check_command: "ruff format --check ."
      lint_command: "ruff check ."
      test_command: "coverage run -m pytest"
      coverage_args: "--report-only"
```

Use copied workflows when:

- the repo has unusual setup
- existing CI is fragile
- deploy behavior is coupled to CI
- this is the first migration PR

Use reusable workflows when:

- the repo's install/lint/test/build commands are clear
- the repo is ready for centralized CI logic
- you want less drift over time

See [`reusable-workflows.md`](reusable-workflows.md) for full detail.

## Agent-assisted adoption

You can ask an AI coding agent to help apply this standard.

Use a focused prompt. Do not ask the agent to modernize the entire repository.

### Prompt for existing repository migration

```text
You are working in this repository.

Goal: adopt repo-standards in a focused, non-invasive standards migration PR.

Use /path/to/repo-standards as the standards source.

Rules:
- Preserve existing deploy behavior.
- Do not change package managers.
- Do not refactor application code.
- Do not fix unrelated lint/audit/coverage debt.
- Add standards infrastructure only.
- Use the detector and assessor from repo-standards.
- Treat detector output as advisory.
- Treat .repo-policy.yml as authoritative after review.

Steps:
1. Run:
   python3 /path/to/repo-standards/scripts/detect_repo_standard.py --repo . --format markdown

2. Run baseline assessment:
   python3 /path/to/repo-standards/scripts/assess_repo_standards.py --repo . --standards /path/to/repo-standards --base-ref main

3. Choose the closest profile and copy the matching repo-policy template to .repo-policy.yml.

4. Add Rulesync config and rules:
   - templates/rulesync.jsonc -> rulesync.jsonc
   - ai/rules/*.md -> .rulesync/rules/

5. Run:
   npx rulesync generate

6. Add governance and non-invasive workflows:
   - CONTRIBUTING.md
   - .github/PULL_REQUEST_TEMPLATE.md
   - semantic-pull-request.yml
   - ai-rules-check.yml
   - docs-check.yml
   - secret-scan.yml
   - dependabot.yml

7. Add or update .gitignore for generated artifacts such as coverage/, htmlcov/, .coverage.

8. Do not modify deploy or release workflows unless explicitly instructed.

9. Run final assessment:
   python3 /path/to/repo-standards/scripts/assess_repo_standards.py --repo . --standards /path/to/repo-standards --base-ref main --run-safe-checks

10. Open a PR titled:
    chore(standards): adopt repo standards

In the PR body, explain what was added, what deploy behavior was preserved, remaining warnings, and any follow-up work.
```

### Prompt for new repository setup

```text
You are creating a new repository using repo-standards.

Use /path/to/repo-standards as the standards source.

Goal:
- initialize standards infrastructure
- choose the closest profile
- create .repo-policy.yml
- add Rulesync source and generated outputs
- add governance files
- add baseline workflows
- run the assessor
- commit with chore(standards): initialize repository standards
```

### GitHub issue template

This repository includes [`.github/ISSUE_TEMPLATE/adopt-repo-standards.yml`](https://github.com/andrewtryder/repo-standards/blob/main/.github/ISSUE_TEMPLATE/adopt-repo-standards.yml) for structured agent-assisted adoption requests.

## Related docs

| Topic | Doc |
|---|---|
| New repo setup (full) | [`new-repository-setup.md`](new-repository-setup.md) |
| Existing repo migration (full) | [`existing-repository-migration.md`](existing-repository-migration.md) |
| Profile detection | [`detection.md`](detection.md) |
| Profiles | [`profiles.md`](profiles.md) |
| Assessment | [`assessment-guide.md`](assessment-guide.md) |
| Reusable workflows (full) | [`reusable-workflows.md`](reusable-workflows.md) |
| Template drift | [`template-drift.md`](template-drift.md) |
