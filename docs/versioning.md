# Versioning

Repo Standards is currently **V1.0**.

The repository previously mixed older `v1.x`, `pre-1.0`, and future-tense V1.0 language while the standards model was evolving. Going forward, public documentation should use **V1.0** for the standards system and `v1.0.0` for the release tag.

## Current status

```text
Current development line: V1.0
Stable release baseline: Textual TUI + modular Repo Standards release
```

The existing CLI tools remain useful and supported during the V1.0 phase:

```text
scripts/detect_repo_standard.py
scripts/apply_repo_standards.py
scripts/assess_repo_standards.py
scripts/model_assisted_repo_detection.py
```

## Why V1.0?

Repo Standards has moved from a set of scripts and templates into a productized standards system. V1.0 represents the first stable experience that another developer can adopt confidently.

The V1.0 release includes:

- a wizard-first migration workflow
- a documented modular standard model
- AI-agent standardization through Rulesync
- CI/CD classification that preserves deploy workflows by default
- expanded repo-type support, including Firebase and Cloudflare Workers
- governance questions for visibility, collaboration, discussions, issue templates, and security policy
- expanded license choices
- representative fixture repositories for local validation

## Release line

| Version | Purpose |
|---|---|
| `V1.0` | Current standards baseline |
| `v1.0.0` | Git tag for the first stable wizard-first Repo Standards release |
| `v1.x` | Backward-compatible additions, new modules, fixture coverage, and documentation improvements |
| `v2.0.0` | Future breaking changes to policy shape, generated files, or adoption behavior |

## Documentation language

Use these terms consistently:

| Preferred | Avoid |
|---|---|
| Repo Standards | repo-standards as a product name in prose |
| V1.0 | `pre-1.0`, `v1.2`, `v1.3`, or future-tense V1.0 |
| `v1.0.0` | older release tag examples |
| Standard reference | mismatched versioned spec names |
| Wizard-first workflow | manual copy/paste as the primary user path |

The package/repository name remains `repo-standards`. The product name in prose is **Repo Standards**.
