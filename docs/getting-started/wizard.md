# Wizard-first adoption

The V1.0 default workflow for Repo Standards is an interactive Textual terminal wizard.

The existing CLI flows in [Using Repo Standards](../using-repo-standards.md), [Existing repository migration](../existing-repository-migration.md), and [New repository setup](../new-repository-setup.md) remain supported for scripted adoption and debugging.

## Why wizard first?

Repo Standards migrations involve decisions that should be explicit:

- Is the repo public or private?
- Which license should it use?
- Is this maintained by one developer or multiple developers?
- Are public contributors expected?
- Should GitHub Discussions be enabled?
- Should public issue templates be included?
- Which AI/editor files should be replaced by Rulesync output?
- Which workflows are deploy/release workflows that must be preserved?
- Which checks are duplicates of standard Repo Standards workflows?
- Which language, platform, deploy, and governance modules apply?

A TUI makes these choices reviewable before any files are changed.

## Launch command

```bash
python3 scripts/repo_standards_wizard.py
```

Common options:

```bash
python3 scripts/repo_standards_wizard.py \
  --repo /path/to/project \
  --standards /path/to/repo-standards
```

## Wizard flow

1. Select the target repository.
2. Confirm existing/new repository mode.
3. Answer governance questions.
4. Run deterministic detection.
5. Optionally run advisory AI inference for ambiguous CI/CD workflows.
6. Review AI-agent cleanup.
7. Review CI/CD classification.
8. Confirm modules and quality gates.
9. Preview the migration plan.
10. Apply confirmed changes.
11. Run Rulesync.
12. Run assessment.
13. Show a PR checklist.

## Governance questions

The wizard asks:

| Question | Why it matters |
|---|---|
| Public or private? | Drives license defaults and public governance expectations |
| Which license? | Prevents accidental open-source or proprietary license changes |
| More than one developer? | Drives CODEOWNERS and branch protection recommendations |
| Public contributors expected? | Drives issue templates, PR templates, and support docs |
| GitHub Discussions enabled? | Determines whether README/contributing docs should mention Discussions |
| Public issue templates needed? | Controls `.github/ISSUE_TEMPLATE/` recommendations |
| Security policy needed? | Controls `SECURITY.md` recommendation |
| CODEOWNERS recommended? | Helps multi-developer repos route reviews |

## AI-agent cleanup

The wizard detects legacy or generated AI/editor instruction files:

```text
AGENTS.md
CLAUDE.md
.cursorrules
.cursor/
.agents/
.antigravity/
```

The wizard requires explicit confirmation before deleting or replacing these files.

Recommended confirmation text:

```text
replace-ai-files
```

After migration, canonical source is:

```text
.repo-policy.yml
rulesync.jsonc
.rulesync/rules/*.md
```

Generated outputs are produced by Rulesync:

```text
AGENTS.md
.cursor/rules/*.mdc
.agents/rules/*.md
.agents/memories/*.md
```

`CLAUDE.md` is treated as legacy/non-standard unless a supported Rulesync target is intentionally added.

## CI/CD review

The wizard should scan:

```text
.github/workflows/*.yml
.github/workflows/*.yaml
.github/dependabot.yml
.github/PULL_REQUEST_TEMPLATE.md
.github/ISSUE_TEMPLATE/*
```

Workflow classifications:

| Classification | Default action |
|---|---|
| `KEEP_DEPLOY` | Preserve |
| `KEEP_RELEASE` | Preserve unless standardizing release flow |
| `REPLACE_STANDARD_CHECK` | Replace after confirmation |
| `REPLACE_DUPLICATE_RELEASE_PLEASE` | Replace after confirmation |
| `REPLACE_DUPLICATE_SECRET_SCAN` | Replace after confirmation |
| `REPLACE_DUPLICATE_DOCS_CHECK` | Replace after confirmation |
| `REPLACE_DUPLICATE_AI_RULES_CHECK` | Replace after confirmation |
| `UNKNOWN_REVIEW_REQUIRED` | Preserve and require review |

Recommended confirmation text:

```text
standardize-ci
```

Deploy, release, publish, Firebase, Cloudflare, GCP, Railway, Docker, and GitHub Pages workflows are preserved by default.

## Plan preview

Before applying, the wizard should show grouped actions:

```text
CREATE
DELETE
REPLACE
UPDATE
MERGE
KEEP
WARN
BLOCK
```

The plan cannot be applied while blockers remain.

## Output files

The wizard should write:

```text
.repo-standards-migration-state.json
.repo-standards-migration-summary.md
```

Assessment output should continue to use `scripts/assess_repo_standards.py`.
