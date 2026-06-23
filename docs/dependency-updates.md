# Dependency Updates

## Dependabot

Dependabot is the baseline dependency update tool for all repositories.

### Template

Copy `templates/dependabot.yml` to `.github/dependabot.yml` in your repo and customize.

The baseline template includes:

| Ecosystem | Directory | Schedule | Notes |
|---|---|---|---|
| GitHub Actions | `/` | Weekly | Updates action versions |
| npm | `/` | Weekly | Groups minor/patch dev dependency updates |
| pip | `/` | Weekly | Python dependency updates |

### Customization

- **Monorepos / nested projects**: Add additional directory entries for each sub-project (e.g., `packages/*`, `apps/*`, `functions/*`).
- **Open PR limits**: Adjust `open-pull-requests-limit` to prevent PR overload.
- **Groups**: Add additional grouping rules for production dependencies when appropriate.
- **Schedule**: Change `weekly` to `daily` or `monthly` based on project needs.

### Python dependencies

Python dependency update strategy (Dependabot for pip, or Renovate) is adopted repo-by-repo. The baseline Dependabot template includes a `pip` entry, but repos may need to adjust it for their specific requirements file layout.

### What Dependabot does NOT do

- Dependabot does not run tests or verify compatibility. CI must catch that.
- Dependabot does not manage system dependencies or Docker images.
- Dependabot is not a replacement for `npm audit` or manual security review of breaking changes.