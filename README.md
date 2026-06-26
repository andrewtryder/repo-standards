# Repo Standards

[![Standards Repo CI](https://github.com/andrewtryder/repo-standards/actions/workflows/standards-repo-ci.yml/badge.svg)](https://github.com/andrewtryder/repo-standards/actions/workflows/standards-repo-ci.yml)
[![Docs Pages](https://github.com/andrewtryder/repo-standards/actions/workflows/docs-pages.yml/badge.svg)](https://github.com/andrewtryder/repo-standards/actions/workflows/docs-pages.yml)
[![Release Please](https://github.com/andrewtryder/repo-standards/actions/workflows/release-please.yml/badge.svg)](https://github.com/andrewtryder/repo-standards/actions/workflows/release-please.yml)
[![Status](https://img.shields.io/badge/status-pre--1.0-orange)](docs/versioning.md)
[![License](https://img.shields.io/github/license/andrewtryder/repo-standards)](LICENSE)
[![Release](https://img.shields.io/github/v/release/andrewtryder/repo-standards?sort=semver)](https://github.com/andrewtryder/repo-standards/releases)

[![Repo Standards logo](docs/assets/brand/repo-standards-logo.svg)](https://andrewtryder.github.io/repo-standards/)

Repo Standards is a reusable standards system for GitHub repositories. It covers repository policy, AI-agent instructions, CI/CD, governance, security, dependency updates, release automation, deployment guidance, and migration assessment.

**Current status:** pre-1.0. The formal v1.0 target is a wizard-first, modular release. See [`docs/versioning.md`](docs/versioning.md) and [`docs/roadmap.md`](docs/roadmap.md).

## Who this is for

Repo Standards is built first for the maintainer standardizing a portfolio of repositories, then for other developers who want to adopt, contribute to, or extend the standard.

It is intended to help with:

- creating consistent new repositories
- migrating existing repositories safely
- standardizing AI-agent/editor instructions
- preserving deployment behavior during migration
- reducing copied-template drift through reusable workflows
- making repository governance explicit

## Recommended path

The v1.0 direction is **wizard first, CLI second, manual copy/paste third**.

| Situation | Start here |
|---|---|
| You want the v1.0 product direction | [`docs/getting-started/wizard.md`](docs/getting-started/wizard.md) |
| You are migrating an existing repository today | [`docs/existing-repository-migration.md`](docs/existing-repository-migration.md) |
| You are setting up a new repository today | [`docs/new-repository-setup.md`](docs/new-repository-setup.md) |
| You need current CLI commands | [`docs/using-repo-standards.md`](docs/using-repo-standards.md) |
| You want to understand the model | [`docs/core/modular-standards.md`](docs/core/modular-standards.md) |

Current CLI foundation:

```bash
python3 scripts/detect_repo_standard.py --repo /path/to/project --format markdown

python3 scripts/apply_repo_standards.py \
  --repo /path/to/project \
  --standards /path/to/repo-standards \
  --mode existing \
  --dry-run
```

## Local checks

Run the same core checks used by the standards repo CI:

```bash
python3 -m compileall scripts
python3 scripts/detect_repo_standard.py --repo . --format markdown
python3 scripts/detect_repo_standard.py --repo . --format json
python3 scripts/check_code_quality_standards.py --repo . --format markdown
python3 scripts/assess_repo_standards.py --repo . --standards . --output-dir /tmp/repo-standards-assessment
python3 scripts/check_docs_ai_rule_sync.py --base-ref main
npx rulesync generate
```

## Core model

Repo Standards is moving toward a modular composition model:

```text
core
+ ai-agents
+ language module
+ framework/platform module
+ deployment module
+ governance modules
```

Examples:

```yaml
modules:
  - core
  - ai-agents
  - python
  - home-assistant
  - github-actions
  - pre-commit
  - dependabot
```

```yaml
modules:
  - core
  - ai-agents
  - typescript-node
  - cloudflare-worker
  - github-actions
  - pre-commit
  - dependabot
```

See [`docs/core/modular-standards.md`](docs/core/modular-standards.md).

## AI-agent standardization

Repo Standards treats AI/editor instructions as generated outputs from Rulesync source.

Canonical source in downstream repositories:

```text
.repo-policy.yml
rulesync.jsonc
.rulesync/rules/*.md
```

Generated outputs:

```text
AGENTS.md
.cursor/rules/*.mdc
.agents/rules/*.md
.agents/memories/*.md
```

`AGENTS.md` is the universal generated AI-agent instruction file. Legacy files such as `CLAUDE.md`, `.cursorrules`, `.cursor/`, `.agents/`, and `.antigravity/` should be reviewed during migration and replaced only after explicit confirmation.

See [`docs/core/ai-agent-standardization.md`](docs/core/ai-agent-standardization.md).

## Documentation

Documentation site: <https://andrewtryder.github.io/repo-standards/>

| Need | Read |
|---|---|
| Versioning and v1.0 target | [`docs/versioning.md`](docs/versioning.md) |
| Roadmap | [`docs/roadmap.md`](docs/roadmap.md) |
| Wizard-first workflow | [`docs/getting-started/wizard.md`](docs/getting-started/wizard.md) |
| Modular model | [`docs/core/modular-standards.md`](docs/core/modular-standards.md) |
| AI-agent standardization | [`docs/core/ai-agent-standardization.md`](docs/core/ai-agent-standardization.md) |
| Governance questions | [`docs/core/governance-model.md`](docs/core/governance-model.md) |
| License choices | [`docs/core/license-selection.md`](docs/core/license-selection.md) |
| Existing repository migration | [`docs/existing-repository-migration.md`](docs/existing-repository-migration.md) |
| New repository setup | [`docs/new-repository-setup.md`](docs/new-repository-setup.md) |
| CLI usage | [`docs/using-repo-standards.md`](docs/using-repo-standards.md) |
| Detection | [`docs/detection.md`](docs/detection.md) |
| Assessment | [`docs/assessment-guide.md`](docs/assessment-guide.md) |
| Standard reference | [`docs/repo-standard-v1.md`](docs/repo-standard-v1.md) |
| Code quality standards | [`docs/code-quality-standards.md`](docs/code-quality-standards.md) |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

When changing Repo Standards, keep docs, templates, and AI rule source aligned. If a change affects how future coding agents should behave, update `ai/rules/*.md` along with the human-facing docs.
