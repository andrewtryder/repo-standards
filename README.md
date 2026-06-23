# Repository Standards Standard v1.2

This blueprint defines the baseline for all repositories.

## Source of truth

Each application repository should own:

```txt
.repo-policy.yml
.rulesync/rules/*.md
```

Generated and committed AI/editor outputs:

```txt
AGENTS.md
.cursor/rules/*.mdc
.agents/rules/*.md
.agents/memories/*.md (when Rulesync `antigravity-ide` target is enabled)
```

Do not edit generated files directly. The `.rulesync/` directory is the canonical source.

### Non-dot `agents/` paths

A flat `agents/` directory (without a leading dot) is **not part of this standard**. If a repo has a top-level `agents/` directory, it should be for a documented purpose (e.g., an actual AI agent application, not IDE configuration). The standard only defines behavior for `.agents/` (dot-prefixed).

## Repository layout

### `configs/`

Contains starter configuration files that repos **should copy** (not reference by symlink or import).

| Path | Purpose |
|---|---|
| `configs/node/commitlint.config.mjs` | commitlint config for Node repos |
| `configs/python/.pre-commit-config.yaml` | Pre-commit hook config for Python repos |
| `configs/python/ruff.toml` | Ruff linter/formatter config for Python repos |

These are **examples to copy and customize**. Repos should copy the relevant config file into their repo and adjust it as needed.

### `templates/`

Contains reusable YAML templates that repos **should copy and adapt** (`templates/repo-policy.*.yml` for repo policy files, `templates/workflows/*.yml` for GitHub Actions workflows).

| Area | Contents |
|---|---|
| `templates/repo-policy.*.yml` | Repo policy profiles for each class (python-service, typescript-cloudflare-worker, typescript-library, typescript-app, python-home-assistant, mixed-special) |
| `templates/workflows/*.yml` | GitHub Actions workflows (CI, release, docs, AI rules, semantic PR, dependabot) |
| `templates/rulesync.jsonc` | Rulesync configuration targeting AGENTS.md, Cursor, and Antigravity IDE |

Repos using these templates should copy the relevant files into their repo at the appropriate paths (`.github/workflows/*.yml`, etc.) and make repo-specific adjustments.

### `ai/rules/`

Contains the **canonical AI/editor rules** that define organization-wide engineering standards. These are the source that gets synced to each downstream repo via Rulesync.

| File | Scope |
|---|---|
| `ai/rules/00-org.md` | Organization-wide rules (commits, CI safety, secrets) |
| `ai/rules/10-typescript.md` | TypeScript/JavaScript standards |
| `ai/rules/20-python.md` | Python standards |

Each downstream repo copies these into its `.rulesync/rules/*.md` directory. Rulesync then generates:

- `AGENTS.md`
- `.cursor/rules/*.mdc`
- `.agents/rules/*.md`
- `.agents/memories/*.md` (from the `antigravity-ide` target)

### `docs/`

| File | Purpose |
|---|---|
| `docs/repo-standard-v1.md` | Full standard specification |
| `docs/migration-order.md` | Migration roadmap and what "migration" means |
| `docs/branch-protection.md` | Required branch protection checks after migration |

### `scripts/`

Automation tools for assessing repo readiness.

## Rulesync targets

The `rulesync.jsonc` template defines three output targets:

| Target | Output files | Purpose |
|---|---|---|
| `agentsmd` | `AGENTS.md` | Universal AI agent instructions (works in any AI coding tool) |
| `cursor` | `.cursor/rules/*.mdc` | Cursor-specific rules for IDE behavior |
| `antigravity-ide` | `.agents/rules/*.md`, `.agents/memories/*.md` | Antigravity (Ante AI) IDE rules |

All three targets are enabled by default. If a downstream repo does not use a particular IDE, its generated directory can be committed but is effectively unused.

**Important:** Rulesync output may list only changed/generated files and should not be the sole source of truth for whether all target outputs exist. To verify that all expected outputs are present, use:

```sh
find AGENTS.md .cursor .agents .rulesync -maxdepth 4 -type f -print | sort
```

### `.agents/memories/` is generated, not runtime junk

The `antigravity-ide` Rulesync target generates both `.agents/rules/*.md` and `.agents/memories/*.md`. The `memories` subdirectory contains generated AI agent knowledge files and should be **committed** if the repo opts into Antigravity IDE support. It is not automatically treated as local runtime junk.

## Commit and PR policy

- Semantic PR title validation **is required in CI** -- enforced by `templates/workflows/semantic-pull-request.yml`.
- Local `commitlint` is **optional/recommended** for Node repos. Pre-commit hooks are **optional/recommended** for Python repos.
- If `commitlint` has `subject-case` disabled, this is intentional: squash-merge PR titles (not individual commits) are the release source of truth.

## Coverage policy

Coverage is **phased and report-only by default**. Repos adopt strict thresholds when ready.

### `.gitignore` guidance

Ensure the following entries are in every repo's `.gitignore`:

```txt
# Build and coverage artifacts
coverage/
htmlcov/
.coverage

# DO NOT ignore .agents/memories/ if using the antigravity-ide Rulesync target
# .agents/memories/ contains generated AI agent knowledge and should be committed
```

Previously tracked `coverage/` files may appear as `D coverage/...` in `git status` after adding `coverage/` to `.gitignore`. This is acceptable cleanup. Adding or modifying generated `coverage/` files (`A coverage/...` or `M coverage/...`) should still be blocked in a standards migration PR.

## Release Please strategies

| Repo type | Template | Notes |
|---|---|---|
| Simple / single-component | `release-please.simple.yml` | General-purpose |
| Node package / library | `release-please.node.yml` | Bumps `package.json` |
| Mixed / monorepo | `release-please.manifest.yml` | Requires manifest files |

## Branch protection

After migration, configure required checks: Semantic Pull Request, AI Rules, CI, Docs, and deploy/release where applicable. See `docs/branch-protection.md`.

## Dependency updates

Dependabot should be configured for GitHub Actions and npm. See `templates/workflows/dependabot.yml`.

## Enforcement levels

### Required everywhere

- Semantic pull request title validation.
- Conventional Commit vocabulary.
- Repository-local `.repo-policy.yml`.
- AI/editor rules generated from Rulesync.
- CI check for install, lint, test/build where applicable.
- Docs check for README plus repository policy.
- No deploy workflow changes unless explicitly requested.

### Required for TypeScript / JavaScript

- npm first, because current repos mostly use package-lock.
- `npm ci`.
- `npm run format:check` if present.
- `npm run lint` if present.
- `npm run typecheck` if present.
- `npm test` if present.
- `npm run build` if present.
- Coverage where test coverage is already practical.

### Required for Python

- Existing package manager first: pip/requirements initially; uv migration later if desired.
- Ruff for lint and format.
- pytest for tests.
- coverage.py / pytest-cov when test coverage is practical.
- pre-commit for local hooks.
- Python typechecking (mypy, pyright) is adopted repo-by-repo.

### Required for release repos

- Release Please.
- Changelog/versioning managed by release PR.
- Publication/deployment remains repo-specific.

### Optional / phase 2

- Codecov or equivalent hosted coverage reporting.
- Strict coverage thresholds.
- Security workflows such as CodeQL and dependency review.
- Full reusable deployment workflows.
- Python dependency update strategy.

## Blocker vs warning guidance

When assessing a standards migration PR, distinguish between:

### Blockers (must fix before merging)

- Missing `.repo-policy.yml`
- Missing `.rulesync/rules/*`
- Missing generated AI/editor files (`AGENTS.md`, `.cursor/rules/*.mdc`, `.agents/rules/*.md`)
- Changed or added generated coverage artifacts (`A coverage/...` or `M coverage/...`)
- Secret-like files in the diff
- Risky deploy changes in a standards-only PR

### Warnings / follow-up work

- Deleted generated coverage artifacts (`D coverage/...` when `coverage/` is in `.gitignore`)
- Low test coverage
- ESLint warnings or errors
- npm audit vulnerabilities
- Legacy stale agent files being removed
- Missing `rulesync` devDependency (acceptable initially, pin later)
