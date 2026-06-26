# AI-agent standardization

Repo Standards uses Rulesync to standardize AI-agent and editor instructions across repositories.

## Policy

`AGENTS.md` is the universal generated AI-agent instruction file.

Generated AI/editor files should not be hand-edited as source material. Change the source files and regenerate outputs instead.

## Source of truth

Canonical source in downstream repositories:

```text
.repo-policy.yml
rulesync.jsonc
.rulesync/rules/*.md
```

Generated outputs:

```text
AGENTS.md
.cursor/rules/*.mdc
.agents/rules/*.md
.agents/memories/*.md
```

## Migration stance

During migration, the wizard should detect:

```text
AGENTS.md
CLAUDE.md
.cursorrules
.cursor/
.agents/
.antigravity/
```

These files and directories may contain old or generated AI/editor instructions. The wizard should offer to replace them with fresh Rulesync output.

Because this is destructive, the wizard must require explicit confirmation before deleting or replacing them.

Recommended confirmation text:

```text
replace-ai-files
```

## `CLAUDE.md`

`CLAUDE.md` is treated as legacy/non-standard unless Repo Standards intentionally adds and documents a supported Rulesync target for it.

Default behavior:

- do not preserve `CLAUDE.md` as authoritative source
- do not delete it silently
- replace it only after confirmation
- standardize on `AGENTS.md` as the universal generated instruction file

## Rulesync source rules

Repo Standards maintains canonical rule templates in:

```text
ai/rules/*.md
```

Downstream repositories copy selected rules to:

```text
.rulesync/rules/*.md
```

Language, framework, deployment, and governance modules may add their own rules.

Example rule layers:

```text
00-org.md
10-typescript.md
20-python.md
30-cloudflare.md
31-firebase.md
40-home-assistant.md
```

## Generated file review

After running Rulesync, review generated outputs before committing:

```bash
find AGENTS.md .cursor .agents .rulesync -maxdepth 4 -type f -print | sort
```

Expected generated outputs depend on enabled Rulesync targets.

## Pull request expectations

A standards migration PR should make clear:

- which AI/editor files were replaced
- that replacement was confirmed
- which `.rulesync/rules/*.md` files are canonical source
- that generated outputs were produced by Rulesync
- that generated outputs were reviewed before commit
