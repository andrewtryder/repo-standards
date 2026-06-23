# Publishing

This document explains how documentation is published for the repo-standards repository.

## Source of truth

Human-facing documentation lives in `docs/*.md`. The GitHub repository README is the landing page for the repo; the [documentation site](https://andrewtryder.github.io/repo-standards/) is built from `docs/` with MkDocs Material.

Do not commit built HTML. The `site/` output directory is gitignored.

## Local preview

```bash
python3 -m pip install -r requirements-docs.txt
mkdocs serve
```

Open `http://127.0.0.1:8000` to preview changes.

Build without serving:

```bash
mkdocs build --strict
```

## CI and deployment

| Check | When | Workflow |
|---|---|---|
| `mkdocs build --strict` | Pull requests and pushes to `main` | [standards-repo-ci.yml](https://github.com/andrewtryder/repo-standards/blob/main/.github/workflows/standards-repo-ci.yml) |
| Deploy to GitHub Pages | Push to `main` when docs change | [docs-pages.yml](https://github.com/andrewtryder/repo-standards/blob/main/.github/workflows/docs-pages.yml) |

Site updates ship with merges to `main`. Release Please tags govern changelog and GitHub releases; they do not gate documentation deployment unless you later change that policy.

## GitHub Pages setup

1. Repository **Settings → Pages**
2. **Build and deployment → Source:** GitHub Actions
3. After the first successful `docs-pages` workflow run, the site is available at `https://andrewtryder.github.io/repo-standards/`

## Repository metadata

Set description, homepage, and topics with `gh` or the helper script:

```bash
./scripts/apply_repo_metadata.sh          # print commands
./scripts/apply_repo_metadata.sh --apply  # run gh repo edit
```

Current intended metadata:

- **Description:** Reusable GitHub repository standards: CI/CD workflows, governance, AI/editor rules, migration assessment, and deployment guidance.
- **Homepage:** `https://andrewtryder.github.io/repo-standards/`
- **Topics:** `github-actions`, `repository-standards`, `standards`, `ci-cd`, `documentation`, `devops`, `python`, `typescript`, `governance`, `dependabot`, `release-please`, `developer-experience`, `best-practices`, `rulesync`, `repository-templates`, `migration`, `code-quality`

## Link hygiene

Docs that reference files outside `docs/` (for example `templates/` or `profiles/`) should use GitHub blob URLs so links work on the published site.

## Making the repository public

After reviewing for secrets and private references:

```bash
gh repo edit andrewtryder/repo-standards --visibility public
```

Public repositories benefit from community health files at the repo root: `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, and `CODE_OF_CONDUCT.md`.
