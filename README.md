# Repo Standards

A reusable standards system for GitHub repositories covering CI/CD, docs, governance, AI/editor rules, dependency updates, release automation, deployment guidance, and migration assessment.

**Current standard: Repo Standard v1.3** — see [`docs/repo-standard-v1.md`](docs/repo-standard-v1.md) for the full specification.

## What this is

This repository defines a baseline standard for existing and future code repositories.

It provides:

- repo policy profiles
- copyable templates
- reusable GitHub Actions workflows
- AI/editor rule synchronization
- migration and assessment tooling
- deployment-provider guidance

## Quick start

### New repository

Read [`docs/new-repository-setup.md`](docs/new-repository-setup.md).

### Existing repository

Read [`docs/existing-repository-migration.md`](docs/existing-repository-migration.md).

### Not sure what applies?

Run the advisory detector:

```bash
python3 scripts/detect_repo_standard.py --repo /path/to/project --format markdown
```

Then create or update `.repo-policy.yml`.

## Source-of-truth model

In each application repository:

- `.repo-policy.yml` defines the adopted standard profile and repo-specific commands.
- `.rulesync/rules/*.md` contains canonical AI/editor rules.
- Generated AI/editor outputs are committed after running Rulesync.

See [`docs/concepts.md`](docs/concepts.md) for the full lifecycle model. For how documentation and AI/editor rules stay aligned, see [`docs/ai-rules-maintenance.md`](docs/ai-rules-maintenance.md).

This repository uses Release Please with the `simple` strategy. Release Please should create the release PR, update `CHANGELOG.md`, and create the GitHub release/tag after the release PR is merged. See [`docs/release-process.md`](docs/release-process.md).

## Documentation

| Need | Read |
|---|---|
| Using repo-standards | [`docs/using-repo-standards.md`](docs/using-repo-standards.md) |
| Core concepts | [`docs/concepts.md`](docs/concepts.md) |
| AI rules maintenance | [`docs/ai-rules-maintenance.md`](docs/ai-rules-maintenance.md) |
| New repo setup | [`docs/new-repository-setup.md`](docs/new-repository-setup.md) |
| Existing repo migration | [`docs/existing-repository-migration.md`](docs/existing-repository-migration.md) |
| Profiles | [`docs/profiles.md`](docs/profiles.md) |
| Detection | [`docs/detection.md`](docs/detection.md) |
| Assessment | [`docs/assessment-guide.md`](docs/assessment-guide.md) |
| Full specification | [`docs/repo-standard-v1.md`](docs/repo-standard-v1.md) |
| Branch protection | [`docs/branch-protection.md`](docs/branch-protection.md) |
| Template drift | [`docs/template-drift.md`](docs/template-drift.md) |
| Reusable workflows | [`docs/reusable-workflows.md`](docs/reusable-workflows.md) |
| Release process | [`docs/release-process.md`](docs/release-process.md) |
| Cloudflare deploy guidance | [`docs/deployment/cloudflare.md`](docs/deployment/cloudflare.md) |
| GCP deploy guidance | [`docs/deployment/gcp.md`](docs/deployment/gcp.md) |
| Railway deploy guidance | [`docs/deployment/railway.md`](docs/deployment/railway.md) |

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

This is a personal/public blueprint. Contributions and suggestions are welcome — please preserve the phased migration approach and the principle that standards should never block useful work over legacy technical debt.
