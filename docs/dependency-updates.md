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

For pip requirements repositories, `requirements.txt` is the runtime dependency
file and `requirements-dev.txt` is the standard development/test dependency
file. Keep pytest, coverage, Ruff, and test helpers out of runtime requirements.
New Python baselines should include `requirements-dev.txt` with at least
`pytest`, `coverage`, and `ruff`. When adopting repo-standards on an existing
repo, `apply_repo_standards.py` merges any missing dev packages into the file
instead of skipping it.

### JavaScript and TypeScript dependencies

For npm, pnpm, yarn, and bun repositories, `devDependencies` is the standard
place for development-only tooling. Put TypeScript, ESLint, Prettier, Vitest,
Jest, Mocha, coverage providers, Rulesync, Commitlint, Husky, lint-staged, and
`@types/*` packages in `devDependencies`. Runtime `dependencies` should only
contain packages needed by the app or library at runtime.

Rulesync is mandatory even when the application is not JavaScript or
TypeScript. Non-Node repos should keep Python/Ruby/etc. development tools in
their native dev dependency mechanism, and use a private tooling-only
`package.json` only for Node-based repository tools such as Rulesync.

### What Dependabot does NOT do

- Dependabot does not run tests or verify compatibility. CI must catch that.
- Dependabot does not manage system dependencies or Docker images.
- Dependabot is not a replacement for `npm audit` or manual security review of breaking changes.
