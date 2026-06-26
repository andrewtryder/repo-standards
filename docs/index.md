# Repo Standards

Repo Standards is a reusable standards system for GitHub repositories. It covers repository policy, AI-agent instructions, CI/CD, governance, security, dependency updates, release automation, deployment guidance, and migration assessment.

**Current status:** pre-1.0. The formal v1.0 release target is the first stable, wizard-first, modular Repo Standards release.

## Start here

| If you want to... | Read this |
|---|---|
| Understand the v1.0 direction | [Roadmap](roadmap.md) |
| Understand versioning | [Versioning](versioning.md) |
| Use the planned wizard-first flow | [Wizard-first adoption](getting-started/wizard.md) |
| Migrate an existing repo with today's CLI | [Existing repository migration](existing-repository-migration.md) |
| Set up a new repo with today's CLI/manual steps | [New repository setup](new-repository-setup.md) |
| Understand the modular model | [Modular standards](core/modular-standards.md) |
| Standardize AI-agent instructions | [AI-agent standardization](core/ai-agent-standardization.md) |
| Choose governance and community settings | [Governance model](core/governance-model.md) |
| Choose a license intentionally | [License selection](core/license-selection.md) |

## Product stance

Repo Standards is built first for a maintainer standardizing a set of repositories, then for other developers who want to adopt, contribute to, or extend the standard.

The planned v1.0 user experience is:

1. Launch the Textual migration wizard.
2. Answer governance and license questions.
3. Review language, platform, and deployment detection.
4. Confirm AI-agent cleanup and Rulesync regeneration.
5. Review CI/CD classification.
6. Apply a safe migration plan.
7. Run assessment.
8. Open a focused standards PR.

Until the wizard is implemented, the current CLI tools remain the supported path.

## What Repo Standards manages

- `.repo-policy.yml` repository policy
- AI-agent/editor rules through Rulesync
- GitHub Actions checks and reusable workflow strategy
- branch protection recommendations
- dependency updates
- release automation
- deployment-provider guidance
- governance files such as `CONTRIBUTING.md`, PR templates, issue templates, `SECURITY.md`, and `CODEOWNERS`
- migration assessment and drift checks

## Source-of-truth model

In downstream repositories:

| Layer | Path | Purpose |
|---|---|---|
| Repo policy | `.repo-policy.yml` | Adopted profile, modules, commands, gates, governance, release, and deploy metadata |
| AI rule source | `.rulesync/rules/*.md` | Canonical AI/editor behavior |
| Rulesync config | `rulesync.jsonc` | Generated target configuration |
| Universal generated instructions | `AGENTS.md` | Generated AI-agent instructions |
| Editor generated outputs | `.cursor/`, `.agents/` | Generated editor-specific rules and memories |

Generated AI/editor files are committed, but they are not the source of truth.

## Contributing

See [CONTRIBUTING.md](https://github.com/andrewtryder/repo-standards/blob/main/CONTRIBUTING.md). Contributions should preserve the phased migration approach and keep docs, templates, and AI rule source aligned.
