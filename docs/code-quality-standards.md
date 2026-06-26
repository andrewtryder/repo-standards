# Code Quality Standards

Repo Standards uses one unified code-quality/tooling standard across languages and file formats.
It does not require every repository to use every tool.

## Core model

- `.repo-policy.yml` is authoritative after adoption.
- The repo profile determines which standards apply to the repository.
- File patterns determine which checks run inside applicable standards.
- CI is the source of truth for merge readiness.
- Pre-commit is optional but recommended for fast local feedback.
- New repositories may adopt stricter defaults immediately.
- Existing repositories should start with warnings or report-only checks where practical.

The conceptual CI gates remain:

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

Repos can disable a gate in `.repo-policy.yml` only when it is not applicable. File-pattern
checks feed into those gates; they do not replace the gate model.

## File-pattern matrix

| Area | File patterns | Default formatter | Default linter/checker | CI gate | Pre-commit |
|---|---|---|---|---|---|
| Python | `*.py` | `ruff format` | `ruff check` | `lint`, `test`, `coverage` | Optional |
| TypeScript/JavaScript | `*.ts`, `*.tsx`, `*.js`, `*.jsx`, `*.mjs`, `*.cjs` | Prettier | ESLint or repo command | `format_check`, `lint`, `typecheck`, `test`, `build` | Optional |
| Shell | `*.sh`, `*.bash` | None | ShellCheck | `lint` | Optional |
| YAML | `*.yml`, `*.yaml` | Prettier or yamllint-compatible formatting | yamllint | `lint` | Optional |
| GitHub Actions | `.github/workflows/*.yml`, `.github/workflows/*.yaml` | YAML formatter | actionlint | `lint` / workflow validation | Optional |
| Markdown | `*.md` | Prettier or mdformat | markdownlint if configured | `docs` | Optional |
| Docker | `Dockerfile`, `Dockerfile.*` | None | hadolint | `lint` / `build` | Optional |
| Make | `Makefile`, `*.mk` | None | checkmake if adopted | `lint` | Optional |
| JSON / JSONC / TOML | `*.json`, `*.jsonc`, `*.toml` | Prettier where applicable | Parser validation or repo command | `lint` | Optional |

These are defaults, not mandates. A repository may use equivalent tools when documented in
`.repo-policy.yml`, package scripts, workflow inputs, or local config.

## Migration behavior

For existing repositories, newly introduced file-pattern checks should be advisory first:

- Missing optional tools are warnings, not blockers.
- Existing CI commands should not be replaced unless the migration explicitly chooses that.
- Deploy, release, publish, package-manager, and application-source behavior must remain unchanged.
- Coverage and language-specific debt should stay report-only until the repository is ready.

For new repositories, use the profile defaults and enable stricter file-pattern checks earlier.

## Local analyzer

Use the read-only analyzer to identify file classes and matching tooling:

```bash
python3 scripts/check_code_quality_standards.py --repo . --format markdown
python3 scripts/check_code_quality_standards.py --repo . --format json
```

Strict mode treats missing expected tooling as failures:

```bash
python3 scripts/check_code_quality_standards.py --repo . --strict
```

Optional tool execution is check-only and never mutates files:

```bash
python3 scripts/check_code_quality_standards.py --repo . --run-tools
```

Unavailable external tools are skipped or warned in normal mode. Use strict mode only for repos
that intentionally adopted those checks.

## Reusable workflow

The optional reusable workflow `.github/workflows/code-quality.reusable.yml` runs the analyzer with
workflow inputs for file-area toggles and strictness. It is not copied or enabled by default during
existing-repo migration.
