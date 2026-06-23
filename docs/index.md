# Repo Standards

A reusable standards system for GitHub repositories covering CI/CD, docs, governance, AI/editor rules, dependency updates, release automation, deployment guidance, and migration assessment.

**Current standard: Repo Standard v1.3**

## Start here

| Situation | Guide |
|---|---|
| Practical adoption with commands | [Using repo-standards](using-repo-standards.md) |
| Brand-new repository | [New repository setup](new-repository-setup.md) |
| Existing repository migration | [Existing repository migration](existing-repository-migration.md) |
| Full specification | [Repo Standard v1.3](repo-standard-v1.md) |

## What this repository provides

- Repo policy profiles and `.repo-policy.yml` templates
- Copyable GitHub Actions workflow templates
- Reusable CI workflows callable from downstream repos
- AI/editor rule synchronization via Rulesync
- Migration assessment and profile detection tooling
- Deployment-provider guidance

## Source of truth

Human-facing guidance lives in this `docs/` directory and in [README.md](https://github.com/andrewtryder/repo-standards/blob/main/README.md) on GitHub.

Template and profile paths (for example `templates/` and `profiles/`) are maintained in the [GitHub repository](https://github.com/andrewtryder/repo-standards). Links to those paths in the docs open on GitHub when needed.

## Contributing

See [CONTRIBUTING.md](https://github.com/andrewtryder/repo-standards/blob/main/CONTRIBUTING.md) on GitHub.
