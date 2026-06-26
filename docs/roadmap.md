# Roadmap

This roadmap describes the path from the current CLI-driven Repo Standards foundation to the formal v1.0 release.

## North star

Repo Standards v1.0 should let a maintainer migrate one repository at a time with a safe, guided terminal wizard while preserving deployment behavior and standardizing AI-agent instructions.

The intended workflow is:

1. Run the wizard.
2. Answer governance and license questions.
3. Review detection.
4. Confirm AI-agent cleanup.
5. Review CI/CD classification.
6. Confirm modules and quality gates.
7. Preview the migration plan.
8. Apply confirmed changes.
9. Run Rulesync and assessment.
10. Open a focused standards PR.

## v1.0 definition

The formal v1.0 release should include:

- Textual TUI as the default documented workflow
- existing repository migration with explicit destructive confirmations
- AI-agent standardization through Rulesync
- `AGENTS.md` as the universal generated AI-agent instruction file
- CI/CD classification that preserves deploy workflows by default
- duplicate standards checks replaced only after confirmation
- modular standards model
- expanded repo-type support:
  - Python service
  - Home Assistant integration
  - TypeScript/Node app
  - TypeScript library
  - Cloudflare Worker
  - Firebase project
  - GCP project
  - Railway project
  - mixed/special repos
- governance questions for:
  - public/private visibility
  - license choice
  - more than one developer
  - public contributors
  - GitHub Discussions
  - issue templates
  - PR templates
  - `SECURITY.md`
  - `CODEOWNERS`
- expanded license options
- contributor and maintainer documentation

## Milestones

### v0.2 — Documentation architecture

- Reposition Repo Standards as pre-1.0.
- Make the docs wizard-first.
- Add versioning and roadmap docs.
- Add modular standards docs.
- Add AI-agent standardization docs.
- Add governance and license selection docs.

### v0.3 — Modular model

- Define module IDs and profile composition.
- Add module metadata for core, AI agents, languages, platforms, deploy providers, and governance.
- Keep `.repo-policy.yml` authoritative after adoption.

### v0.4 — Textual TUI skeleton

- Add optional Textual dependency.
- Add `scripts/repo_standards_wizard.py`.
- Let users choose a repo and run detection.
- Write and resume migration state.

### v0.5 — AI-agent cleanup workflow

- Detect legacy AI/editor files:
  - `AGENTS.md`
  - `CLAUDE.md`
  - `.cursorrules`
  - `.cursor/`
  - `.agents/`
  - `.antigravity/`
- Require explicit confirmation before deleting or replacing.
- Regenerate outputs with Rulesync.

### v0.6 — CI/CD classifier

- Classify `.github/workflows/*`.
- Preserve deploy/release/publish workflows by default.
- Identify duplicate standards-owned checks.
- Use AI inference only as advisory context for ambiguous workflows.

### v0.7 — Expanded repo-type support

- Add Firebase detection and docs.
- Refine Home Assistant and pure Python guidance.
- Document repo-type module combinations.

### v0.8 — Contributor and maintainer docs

- Expand contributor guidance.
- Add maintainer docs for adding modules, profiles, templates, and AI rules.
- Add a docs style guide.

### v0.9 — Release candidate

- Validate the wizard across representative repositories.
- Ensure docs and AI rules are aligned.
- Freeze breaking changes unless required for v1.0 safety.

### v1.0 — Formal release

- Publish the first stable wizard-first Repo Standards release.
