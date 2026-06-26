# Modular standards

Repo Standards is moving toward a modular composition model.

Instead of treating each repository as exactly one profile, Repo Standards should compose a standard from core behavior plus selected modules.

## Composition model

```text
Repo Standards
= core
+ ai-agents
+ language module
+ framework/platform module
+ deployment module
+ governance modules
```

Profiles remain useful as presets. A profile should describe a common module combination, not become a monolithic rule set.

## Core module

The core module applies to every repository.

It includes:

- `.repo-policy.yml`
- semantic PR title validation
- basic governance files
- secret scanning
- dependency updates
- assessment
- safe migration principles

## AI agents module

The `ai-agents` module should be enabled for every repository.

It includes:

- `rulesync.jsonc`
- `.rulesync/rules/*.md`
- generated `AGENTS.md`
- generated editor rule outputs
- drift checks that ensure generated files match source

See [AI-agent standardization](ai-agent-standardization.md).

## Language modules

Language modules define expected checks and tooling without changing package managers during baseline migrations.

| Module | Typical checks |
|---|---|
| `python` | Ruff, pytest, coverage |
| `typescript-node` | format, lint, typecheck, test, coverage, build |

## Framework and platform modules

Framework/platform modules refine behavior for common repository shapes.

| Module | Purpose |
|---|---|
| `home-assistant` | Home Assistant custom components/integrations |
| `cloudflare-worker` | Cloudflare Workers and Wrangler-based projects |
| `firebase` | Firebase projects and Firebase deploy workflows |
| `gcp` | Google Cloud deploy workflows |
| `railway` | Railway deploy workflows |

## Governance modules

Governance modules are driven by wizard questions.

| Module | When to enable |
|---|---|
| `issue-templates` | Public users or contributors should submit issues |
| `security-policy` | Security reporting process should be documented |
| `codeowners` | More than one developer or team-based review ownership |
| `github-discussions` | Discussions are enabled for support, design, or contributor Q&A |
| `github-pages-docs` | The repo publishes docs with GitHub Pages |

## Example module set

```yaml
modules:
  - core
  - ai-agents
  - python
  - github-actions
  - pre-commit
  - dependabot
```

```yaml
modules:
  - core
  - ai-agents
  - typescript-node
  - firebase
  - github-actions
  - pre-commit
  - dependabot
```

## `.repo-policy.yml`

After adoption, `.repo-policy.yml` is authoritative. Detection recommends modules and profiles, but the repo owner confirms what the repository actually adopts.

Recommended future shape:

```yaml
name: example-project
profile: firebase-app
visibility: public
license: Apache-2.0

modules:
  - core
  - ai-agents
  - typescript-node
  - firebase
  - github-actions
  - pre-commit
  - dependabot
```

## Migration rule

For existing repositories, the first migration should be conservative:

- preserve deploy behavior
- preserve package manager
- avoid application source refactors
- avoid unrelated technical debt cleanup
- standardize AI-agent instructions only after confirmation
- replace duplicate standard CI/CD checks only after confirmation
