# Documentation overhaul plan

This plan tracks the documentation architecture changes needed before the formal v1.0 Repo Standards release.

## Goals

- Make Repo Standards wizard-first.
- Reposition the project as pre-1.0 until the TUI workflow is stable.
- Make the modular standard model explicit.
- Document AI-agent standardization as a user-facing concept.
- Document governance and license questions.
- Prepare the docs for both the primary maintainer workflow and outside developer contribution.

## Primary audiences

1. The maintainer standardizing a portfolio of repositories.
2. Other developers adopting, contributing to, or extending Repo Standards.

## Current issues

- The docs contain useful content but lack a clear reader journey.
- The README and docs homepage are too small to guide new users.
- `Repo Standard v1.3` language implies more stability than the current direction intends.
- Profiles are documented, but modules are not yet first-class in the docs.
- AI-agent standardization is mostly covered as maintenance guidance instead of adoption guidance.
- Firebase is not yet a first-class documented repo type.
- Contributor docs are accurate but too thin for outside contributors.
- GitHub Models migration appears in more than one navigation section.

## Proposed documentation architecture

- Getting started
  - Wizard-first adoption
  - Existing repository migration
  - New repository setup
  - Migration checklist
- Core model
  - Modular standards
  - AI-agent standardization
  - Governance model
  - License selection
  - Profiles
  - Detection
- Migration tools
  - CLI usage
  - Assessment
  - GitHub Models advisory
- CI/CD and automation
  - Reusable workflows
  - Template drift
  - Branch protection
  - Release process
- Security and dependencies
  - Secret scanning
  - License scanning
  - Dependency updates
- Deployment
  - Cloudflare
  - GCP
  - Railway
  - Firebase
- Maintainers
  - Contributing
  - Adding a module
  - Adding a profile
  - Docs and AI-rule sync
  - Publishing docs
- Reference
  - Standard reference

## Initial implementation

This PR should:

- update the README
- update the docs homepage
- add versioning and roadmap pages
- add wizard-first adoption docs
- add modular standards docs
- add AI-agent standardization docs
- add governance and license selection docs
- update MkDocs navigation

## Later work

- Add Firebase deployment guidance.
- Add repo-type guides.
- Expand contributor and maintainer documentation.
- Add a docs style guide.
- Update AI rules to match new user-facing docs when behavior changes.
