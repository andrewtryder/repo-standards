# Versioning

Repo Standards is currently **pre-1.0**.

The repository previously used `Repo Standard v1.3` language while the standards model was evolving. Going forward, public documentation should treat the project as pre-1.0 until the wizard-first, modular workflow is stable enough to be the formal v1.0 release.

## Current status

```text
Current development line: pre-1.0
Formal v1.0 target: Textual TUI + modular Repo Standards release
```

The existing CLI tools remain useful and supported during the pre-1.0 phase:

```text
scripts/detect_repo_standard.py
scripts/apply_repo_standards.py
scripts/assess_repo_standards.py
scripts/model_assisted_repo_detection.py
```

## Why reset to pre-1.0?

Repo Standards is moving from a set of scripts and templates into a productized standards system. The formal v1.0 should represent the first stable experience that another developer can adopt confidently.

The v1.0 release should include:

- a wizard-first migration workflow
- a documented modular standard model
- AI-agent standardization through Rulesync
- CI/CD classification that preserves deploy workflows by default
- expanded repo-type support, including Firebase
- governance questions for visibility, collaboration, discussions, issue templates, and security policy
- expanded license choices
- contributor and maintainer documentation

## Suggested pre-1.0 milestones

| Milestone | Purpose |
|---|---|
| `v0.1` | Existing CLI, detection, apply, and assessment foundation |
| `v0.2` | Documentation architecture overhaul |
| `v0.3` | Modular profile/module model |
| `v0.4` | Textual TUI skeleton |
| `v0.5` | AI-agent cleanup and Rulesync regeneration workflow |
| `v0.6` | CI/CD classifier and advisory AI inference |
| `v0.7` | Firebase and expanded repo-type support |
| `v0.8` | Contributor and maintainer documentation |
| `v0.9` | v1.0 release candidate |
| `v1.0` | First stable wizard-first Repo Standards release |

## Documentation language

Use these terms consistently:

| Preferred | Avoid |
|---|---|
| Repo Standards | repo-standards as a product name in prose |
| pre-1.0 | current standard v1.3 |
| Standard reference | Repo Standard v1.3 specification |
| Wizard-first workflow | one-command apply as the primary user path |

The package/repository name remains `repo-standards`. The product name in prose is **Repo Standards**.
