# Repo Standard v1.3

## 1. Commit and PR policy

Use Conventional Commits syntax:

```txt
<type>[optional scope]: <description>
```

Allowed types:

```txt
feat
fix
docs
refactor
test
chore
ci
build
perf
revert
style
```

### Required CI gate

- **Semantic PR title validation is required in CI.**
- The `semantic-pull-request.yml` workflow validates every PR title.
- This is the non-negotiable source of truth for release notes and changelogs.

### Optional local gate

- `commitlint` (via Husky for Node repos) or `pre-commit` hooks (for Python repos) are **optional but recommended** for local feedback.
- If `commitlint` is configured with `subject-case` disabled (`[0]`), this is intentional: squash-merge PR titles (not individual commits) are the release source of truth. Lowercasing individual commit subjects would not meaningfully improve the final squash message and would add friction to local commits.

### Recommended merge style

- Squash merge.
- The squash commit title should be the validated PR title.

## 2. Release policy

Use Release Please for repos that publish packages, GitHub releases, or user-facing deployable artifacts.

### Release Please strategies

Choose the workflow template that matches the repo type:

| Repo type | Template | Notes |
|---|---|---|
| Simple / single-component | `release-please.simple.yml` | General-purpose; no package.json version file |
| Node package / library | `release-please.node.yml` | Bumps `package.json` version automatically |
| Mixed / monorepo | `release-please.manifest.yml` | Requires `.release-please-manifest.json` + `release-please-config.json` |

- **Node package/library repos** should use the Node-specific release template (`release-please.node.yml`).
- **Mixed repos** (multiple languages, monorepos) should prefer manifest mode (`release-please.manifest.yml`).

Release Please should:

- Create or update release PRs from Conventional Commit history.
- Maintain changelog.
- Bump versions where the repo has version files.
- Create GitHub releases.

Release Please should not be treated as the deploy tool. Deployment remains in repo-specific workflows.

## 3. AI/editor instruction policy

Use Rulesync.

Canonical files:

```txt
.rulesync/rules/*.md
rulesync.jsonc
.repo-policy.yml
```

Generated files:

```txt
AGENTS.md
.cursor/rules/*.mdc
.agents/rules/*.md
.agents/memories/*.md   (when `antigravity-ide` target is enabled)
```

The CI check should regenerate and fail if generated files drift.

### Non-dot `agents/` paths

A top-level `agents/` directory (without a leading dot) is **not part of this standard**. The standard only defines behavior for `.agents/`. If a repo has a flat `agents/` directory, it should be for a documented purpose (e.g., an actual AI agent application). The standard's checks will flag `agents/` as suspicious unless a documented exception exists.

### Rulesync targets

The `rulesync.jsonc` template defines three targets:

| Target | Output | Purpose |
|---|---|---|
| `agentsmd` | `AGENTS.md` | Universal AI agent instructions (works in any AI coding tool) |
| `cursor` | `.cursor/rules/*.mdc` | Cursor-specific rules for IDE behavior |
| `antigravity-ide` | `.agents/rules/*.md`, `.agents/memories/*.md` | Antigravity (Ante AI) IDE rules |

All three targets are enabled by default. If a downstream repo does not use a particular IDE, its generated directory can be committed but is effectively unused until that IDE is used.

**Important:** Rulesync output may list only changed/generated files and should not be the sole source of truth for whether all target outputs exist. To verify that all expected outputs are present, use:

```sh
find AGENTS.md .cursor .agents .rulesync -maxdepth 4 -type f -print | sort
```

### `.agents/memories/` is generated, not runtime junk

The `antigravity-ide` Rulesync target generates both `.agents/rules/*.md` and `.agents/memories/*.md`. The `memories` subdirectory is a valid generated output containing AI agent knowledge. If the repo opts into Antigravity IDE support, `.agents/memories/` should be committed, not ignored.

If `.agents/memories/` exists but `rulesync.jsonc` does not contain `antigravity-ide`, that should be flagged for manual review (it may be stale or misconfigured).

## 4. CI quality gates

Every repo should expose the same conceptual gates, even if the commands differ:

```txt
install
format_check
lint
typecheck
test
coverage
build
docs
```

A gate may be explicitly disabled in `.repo-policy.yml` only when it is not applicable.

### Node version management

Node/TypeScript repositories **must have a root `.nvmrc` file** specifying the project's Node.js version (e.g., `24`).

- `.nvmrc` is the operational source of truth for local development (`nvm use`, `fnm`, etc.) and CI (`node-version-file`).
- The `node_version` field in `.repo-policy.yml` is **descriptive** -- it documents the intended version, but `.nvmrc` drives actual setup.
- CI workflow templates use `node-version-file: ".nvmrc"` instead of hardcoded `node-version`.

A template `.nvmrc` (with `24`) is at `configs/node/.nvmrc`.

### Reusable workflow inputs

When writing CI workflows, prefer using `workflow_call` with inputs so that runtime versions and commands are configurable per-repo:

| Input | Default | Purpose |
|---|---|---|
| `node_version` | `""` (uses `.nvmrc`) | Node.js version for setup-node |
| `python_version` | `"3.12"` | Python version for setup-python |
| `install_command` | `"npm ci"` or pip command | Install dependencies |
| `lint_command` | `"npm run lint"` or `"ruff check ."` | Lint check |
| `typecheck_command` | `"npm run typecheck"` or `""` | Type checking |
| `test_command` | `"npm test"` or `"pytest"` | Run tests |
| `coverage_command` | `"npm run test:coverage"` or coverage run | Coverage report |
| `build_command` | `"npm run build"` or `""` | Build step |

### Reusable workflows (long-term preferred)

The preferred long-term CI standard is **GitHub reusable workflows** defined in repo-standards and called from downstream repos. This reduces template drift and ensures updates flow automatically.

See `docs/template-drift.md` for details and caller examples.

Reusable workflow templates are at:

- `templates/workflows/node-ci.reusable.yml`
- `templates/workflows/python-ci.reusable.yml`

## 5. Coverage policy

Coverage should be phased in.

Baseline:

- Generate coverage report where tests already exist.
- Do not block merges on strict percentage initially.

Phase 1:

- Enforce coverage only for repos with existing coverage scripts.
- Use repo-local thresholds.

Phase 2:

- Enforce patch/diff coverage for changed code.
- Increase thresholds gradually.

Default starting thresholds:

```txt
libraries: 80% lines / 70% branches
services/workers: 70% lines / 60% branches
legacy/mixed repos: report-only until stable
```

Do not fail a useful bugfix because a legacy repo has poor historical coverage. Prefer changed-code coverage first.

Coverage remains **report-only** unless a repo has stable thresholds.

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

Previously tracked `coverage/` files may appear as `D coverage/...` in `git status` after adding `coverage/` to `.gitignore`. This is **acceptable cleanup** -- not a blocker. Adding or modifying generated `coverage/` files (`A coverage/...` or `M coverage/...`) should still be a blocker in a standards migration PR.

## 6. Docs policy

Required docs:

```txt
README.md
.repo-policy.yml
AGENTS.md
```

Recommended docs:

```txt
docs/development.md
docs/deployment.md
docs/release.md
```

Required README concepts (validated by docs-check.yml via keyword/concept matching, not exact headings):

```txt
Overview
Local development
Checks (CI, quality gates, lint, test, etc.)
Deployment or release process
Environment variables / secrets (or "None required")
AI/editor instructions
```

A repo with no environment variables may satisfy the requirement with "None required."

## 7. Repo classes

Use these profiles:

```txt
typescript-library
typescript-cloudflare-worker
typescript-app
python-home-assistant
python-service
mixed-special
```

The profile determines CI defaults and migration risk.

### Profile templates

Each profile template (under `templates/repo-policy.*.yml`) includes:

| Field | Description |
|---|---|
| `name` | Descriptive example name |
| `profile` | Profile identifier |
| `node_version` / `python_version` / `package_manager` | Runtime configuration (descriptive; `.nvmrc` is operational for Node) |
| `commands` | Install, format, lint, typecheck, test, coverage, build |
| `quality_gates` | Required checks |
| `release` | Release Please configuration |
| `deploy` | Deploy provider and workflow |
| `migration_notes` | Notes specific to this profile's migration |

### Python typechecking

Python typechecking (mypy, pyright, etc.) is **adopted repo-by-repo**. It is not enforced globally. Templates include an empty `typecheck: ""` field and a comment explaining the policy. Individual repos may add a typecheck command when ready.

## 8. Dependency updates

### Dependabot

Dependabot is the baseline dependency update tool for all repositories.

Copy `templates/dependabot.yml` to `.github/dependabot.yml` in each repo.

The template includes weekly updates for:

- GitHub Actions
- npm (root directory, with grouped dev dependency updates)
- pip (root directory)

For monorepos or repos with nested projects, add additional directory entries for each sub-project.

See `docs/dependency-updates.md` for customization guidance.

## 9. Secret scanning

A baseline secret scanning workflow is at `templates/workflows/secret-scan.yml`.

The workflow uses **TruffleHog** to scan PR diffs for verified secrets. It is configured conservatively (`--results=verified`) to reduce false positives.

Branch protection should require the Secret Scan check once it passes consistently in a repo.

See `docs/security-scanning.md` for configuration and recommended workflow.

## 10. Template drift management

Repo-standards supports two approaches for managing template drift:

| Approach | When to use |
|---|---|
| **Copied templates** (default) | Initial migration, early adoption. Templates are copied into each repo. Drift must be reassessed manually. |
| **GitHub reusable workflows** (preferred long-term) | After the standard stabilizes. Workflows live in repo-standards and are called from downstream repos. Updates flow automatically. |

See `docs/template-drift.md` for caller examples and migration guidance.

## 11. Branch protection

After migration, the following required checks should be configured in branch protection rules for the default branch:

| Check | Required when |
|---|---|
| Semantic Pull Request | Always |
| AI Rules | Always (if `.rulesync/` is present) |
| CI | Always |
| Docs | Always |
| Secret Scan | Recommended (once it passes consistently) |
| Deploy check | When deploy workflow is configured |
| Release check | When Release Please is configured |

See `docs/branch-protection.md` for details.

## 12. Blocker vs warning guidance

When assessing a standards migration PR, the assessor should distinguish between:

### Blockers (must fix before merging)

- Missing `.repo-policy.yml`
- Missing `.rulesync/rules/*`
- Missing generated AI/editor files (`AGENTS.md`, `.cursor/rules/*.mdc`, `.agents/rules/*.md`)
- Changed or added generated coverage artifacts (`A coverage/...` or `M coverage/...`)
- Secret-like files in the diff
- Risky deploy changes in a standards-only PR

### Warnings / follow-up work (standard migration is acceptable)

- Deleted generated coverage artifacts (`D coverage/...` when `coverage/` is in `.gitignore`)
- Low test coverage
- ESLint warnings or errors
- npm audit vulnerabilities
- Legacy stale agent files being removed
- Missing `rulesync` devDependency (acceptable initially, pin later)
- Missing `.nvmrc` in a Node repo (recommended but not yet required)
- Missing `.github/dependabot.yml` (recommended but not yet required)
- Missing secret scanning workflow (recommended but not yet required)