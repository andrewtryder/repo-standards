# Local Docker test harness

Reproducible end-to-end tests for repo-standards against committed sample repositories.

## Prerequisites

- Docker
- Python 3.12+ (for running the harness on the host)
- PyYAML (`python3 -m pip install pyyaml`) when not using Docker
- [nektos/act](https://github.com/nektos/act) for optional GitHub Actions simulation (`brew install act`)

## Fixtures

| Fixture | Language / stack | Detection profile | Notes |
|---------|------------------|-------------------|-------|
| `python-service` | Python + pytest + ruff | `python-service` | Minimal service layout |
| `typescript-app` | TypeScript + vitest + eslint | `typescript-app` | Covers JavaScript/TypeScript apps |
| `cloudflare-worker` | TypeScript + wrangler | `typescript-cloudflare-worker` | Worker entry + `wrangler.toml` |
| `home-assistant` | HA custom component | `python-service` (forced `python-home-assistant`) | Profile override via agent flags |

Each fixture is a regular codebase with minimal CI. The harness copies it into a temp git repo, runs detect → apply → assess, and checks expected files.

## Quick start

From the repo root:

```bash
make -C tests build
make -C tests test-fixtures
```

Or on the host (requires network for `npx rulesync` and `npm ci` during assessment):

```bash
python3 -m pip install pyyaml
python3 tests/harness/run_fixtures.py --standards .
```

For local offline validation, skip Rulesync and assessment while still checking detection, apply, generated source files, and CI callers:

```bash
make -C tests test-fixtures-offline
python3 tests/harness/run_fixtures.py --standards . --skip-assess --skip-rulesync
```

Run a single fixture:

```bash
python3 tests/harness/run_fixtures.py --standards . --fixture python-service
```

## Simulate GitHub Actions with act

After the harness applies standards to a fixture, run the generated CI workflow locally:

```bash
make -C tests test-act FIXTURE=python-service
make -C tests test-act FIXTURE=typescript-app
```

This:

1. Applies standards into `tests/.work/<fixture>/`
2. Runs `act push` against `.github/workflows/ci.yml`
3. Remaps `andrewtryder/repo-standards@v1.0.0` to your local checkout via `--local-repository`

`tests/.actrc` pins the runner image. The Makefile injects the machine-specific local-repository path.

### act scope

- **In scope:** generated `ci.yml` (node/python reusable CI) and `ai-rules-check.yml` when invoked manually
- **Out of scope / best-effort:** `semantic-pull-request.yml`, `secret-scan.yml` (need live GitHub PR context)

## Optional GitHub CI

The harness is primarily local. An opt-in workflow is available:

- [`.github/workflows/fixture-harness.yml`](../.github/workflows/fixture-harness.yml)
- Triggered by **workflow_dispatch** (manual) or pull requests that change `tests/**` or core scripts
- Does **not** run in required `standards-repo-ci.yml`
- Optional label `run-fixtures` can be used to signal intent on broader PRs (manual dispatch recommended)

## Layout

```
tests/
  Dockerfile              # Toolchain image (python, node, ruff, pytest, pyyaml)
  Makefile                # build, test-fixtures, test-act, clean
  .actrc                  # act runner image pin
  README.md
  fixtures/               # Sample repos
  harness/
    run_fixtures.py       # Orchestrator
    expectations.yml      # Per-fixture golden expectations
    events/               # act event payloads
```

## Troubleshooting

- **PyYAML missing:** `python3 -m pip install pyyaml` or use `make -C tests test-fixtures` (Docker image includes it).
- **rulesync / npm failures:** ensure network access, or use `--skip-rulesync --skip-assess` for offline apply validation.
- **act reusable workflow not found:** confirm `andrewtryder/repo-standards@v1.0.0` maps to an absolute path of this git checkout and that the checkout has tag/ref `v1.0.0` or matching ref.
