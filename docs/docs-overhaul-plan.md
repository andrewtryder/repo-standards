# Documentation overhaul status

This page records the documentation architecture work that shaped the V1.0 Repo Standards release.

## Goals

- Make Repo Standards wizard-first.
- Keep the project consistently described as V1.0.
- Make the modular standard model explicit.
- Document AI-agent standardization as a user-facing concept.
- Document governance and license questions.
- Prepare the docs for both the primary maintainer workflow and outside developer contribution.

## Primary audiences

1. The maintainer standardizing a portfolio of repositories.
2. Other developers adopting, contributing to, or extending Repo Standards.

## Historical issues addressed

- The docs contained useful content but lacked a clear reader journey.
- The README and docs homepage were too small to guide new users.
- Version language was inconsistent across documents.
- Profiles were documented before modules became first-class in the docs.
- AI-agent standardization was mostly covered as maintenance guidance instead of adoption guidance.
- Firebase was not yet a first-class documented repo type.
- Contributor docs needed more maintainer workflow context.

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

## V1.0 implementation

V1.0 includes:

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
