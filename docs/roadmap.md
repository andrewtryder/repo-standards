# Roadmap

This roadmap tracks the current V1.0 baseline and future improvement areas.

## North star

Repo Standards V1.0 lets a maintainer migrate one repository at a time with a safe, guided terminal wizard while preserving deployment behavior and standardizing AI-agent instructions.

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

## V1.0 baseline

The current V1.0 release includes:

- Textual TUI as the default documented workflow
- existing repository migration with explicit destructive confirmations
- AI-agent standardization through Rulesync
- `AGENTS.md` as the universal generated AI-agent instruction file
- CI/CD classification that preserves deploy workflows by default
- duplicate standards checks replaced only after confirmation
- modular standards model
- representative repo-type support:
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
- local fixture testing across representative repositories

## Future work

### Documentation

- Keep docs wizard-first.
- Expand contributor and maintainer documentation.
- Add a docs style guide.

### Modular model

- Expand module metadata for core, AI agents, languages, platforms, deploy providers, and governance.
- Keep `.repo-policy.yml` authoritative after adoption.

### Textual TUI

- Continue improving the wizard flow, review screens, and resume behavior.
- Keep optional Textual dependencies isolated in `requirements-tui.txt`.

### AI-agent cleanup workflow

- Continue detecting legacy AI/editor files:
  - `AGENTS.md`
  - `CLAUDE.md`
  - `.cursorrules`
  - `.cursor/`
  - `.agents/`
  - `.antigravity/`
- Require explicit confirmation before deleting or replacing.
- Regenerate outputs with Rulesync.

### CI/CD classifier

- Preserve deploy/release/publish workflows by default.
- Improve classification for ambiguous workflows.
- Use AI inference only as advisory context.

### Expanded repo-type support

- Continue expanding Firebase detection and docs.
- Refine Home Assistant and pure Python guidance.
- Document repo-type module combinations.

### Fixture harness

- Validate the wizard across representative repositories.
- Add fixtures as new supported repo types are introduced.
- Keep local-only testing available before enabling broader CI requirements.
