# Release process

This repository uses Release Please for standard releases.

Release Please owns:

- release PRs
- `CHANGELOG.md`
- GitHub releases
- version tags such as `v1.3.0`

Normal release flow:

1. Merge conventional commits to `main`.
2. Release Please opens or updates a release PR.
3. Review the generated changelog.
4. Merge the release PR.
5. Release Please creates the GitHub release and tag.

Manual tags are only for exceptional bootstrapping cases.

## This repository

The `repo-standards` repository uses Release Please with the `simple` strategy. Release Please should create the release PR, update `CHANGELOG.md`, and create the GitHub release/tag after the release PR is merged.

Release Please depends on [Conventional Commits](https://www.conventionalcommits.org/) in merge/squash commit titles. Recent history on `main` follows that pattern. If Release Please does not open a release PR after enabling the workflow, check workflow logs and commit titles before falling back to a manual annotated tag.

## Consumer repositories

Release Please owns release PRs, changelog updates, GitHub releases, and tags for repositories that enable it. Do not manually edit `CHANGELOG.md` or create release tags for normal releases unless intentionally bypassing Release Please.

See [`repo-standard-v1.md`](repo-standard-v1.md) for Release Please strategy selection and [`templates/workflows/release-please.simple.yml`](../templates/workflows/release-please.simple.yml) for the canonical workflow template.
