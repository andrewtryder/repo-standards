# nab-api Standards Migration Assessment v3

Generated: `2026-06-23T04:26:46.880387+00:00`
Repo: `/path/to/example-repo`
Standards repo: `/path/to/repo-standards`
Score: **96/100**

## Verdict

Looks ready for review. Remaining items are warnings or follow-up work.

## Blockers

- None detected

## Warnings

- .agents/memories/ is in the diff but antigravity-ide target is NOT configured in rulesync.jsonc. Manual review required.
- Coverage is low: 8.29% lines, 8.64% branches. Keep coverage as report-only.
- Deleted coverage artifacts detected (20 files). This is acceptable cleanup when coverage/ is in .gitignore.
- ESLint passed but reported 20 warnings (and 0 errors if any)
- npm audit reported 7 vulnerabilities (1 low, 2 moderate, 4 high)

## Changed-file hygiene

### generated_artifacts
- `coverage/base.css`
- `coverage/block-navigation.js`
- `coverage/browser.ts.html`
- `coverage/discovery.ts.html`
- `coverage/favicon.png`
- `coverage/find-missing.ts.html`
- `coverage/fix-state.ts.html`
- `coverage/index.html`
- `coverage/index.ts.html`
- `coverage/parser.ts.html`
- `coverage/patch-state.ts.html`
- `coverage/prettify.css`
- `coverage/prettify.js`
- `coverage/scraper.ts.html`
- `coverage/sort-arrow-sprite.png`
- `coverage/sorter.js`
- `coverage/state.ts.html`
- `coverage/test-db.ts.html`
- `coverage/xml-builder.ts.html`
- `coverage/xml-to-sqlite.ts.html`

### agent_memories
- `.agents/memories/10-repo.md`
- `.agents/memories/20-quality-gates.md`
- `.agents/memories/30-deploy.md`

### suspicious_agents_paths
- None

### risky_deploy_files
- None

### secretish_files
- None

## Coverage detail

- Added or modified: []
- Deleted: ['coverage/base.css', 'coverage/block-navigation.js', 'coverage/browser.ts.html', 'coverage/discovery.ts.html', 'coverage/favicon.png', 'coverage/find-missing.ts.html', 'coverage/fix-state.ts.html', 'coverage/index.html', 'coverage/index.ts.html', 'coverage/parser.ts.html', 'coverage/patch-state.ts.html', 'coverage/prettify.css', 'coverage/prettify.js', 'coverage/scraper.ts.html', 'coverage/sort-arrow-sprite.png', 'coverage/sorter.js', 'coverage/state.ts.html', 'coverage/test-db.ts.html', 'coverage/xml-builder.ts.html', 'coverage/xml-to-sqlite.ts.html']
- .gitignore has coverage/: True

## Command analysis

- `eslint_errors`: `0`
- `eslint_warnings`: `20`
- `npm_vulnerabilities`: `7`
- `npm_vulnerability_detail`: `1 low, 2 moderate, 4 high`
- `coverage`: `{'statements': 8.01, 'branches': 8.64, 'functions': 9.61, 'lines': 8.29}`

## Recommendations

- Keep coverage as report-only for this repo; do not add a threshold until coverage is improved.
- Track existing ESLint warnings as technical debt; do not fix them in the standards PR unless trivial.
- Open a separate dependency-audit PR; do not mix audit fixes into the standards PR.
- Review .agents/memories/ -- if intentional, add antigravity-ide to rulesync.jsonc targets.

## Standards feedback

- No repo-standards blueprint changes suggested by this assessment.

## Full state

```json
{
  "ai": {
    "agents_memory_files": [
      ".agents/memories/10-repo.md",
      ".agents/memories/20-quality-gates.md",
      ".agents/memories/30-deploy.md"
    ],
    "agents_rule_files": [
      ".agents/rules/10-repo.md",
      ".agents/rules/20-quality-gates.md",
      ".agents/rules/30-deploy.md"
    ],
    "cursor_rule_files": [
      ".cursor/rules/00-org.mdc",
      ".cursor/rules/10-repo.mdc",
      ".cursor/rules/20-quality-gates.mdc",
      ".cursor/rules/30-deploy.mdc"
    ],
    "has_agents_md": true,
    "has_agents_memories_dir": true,
    "has_agents_rules_dir": true,
    "has_antigravity_target_in_config": false,
    "has_cursor_rules_dir": true,
    "has_repo_policy": true,
    "has_rulesync_config": true,
    "has_rulesync_rules_dir": true,
    "rule_files": [
      ".rulesync/rules/00-org.md",
      ".rulesync/rules/10-repo.md",
      ".rulesync/rules/20-quality-gates.md",
      ".rulesync/rules/30-deploy.md"
    ],
    "rulesync_mentions_agentsmd": true,
    "rulesync_mentions_antigravity": true,
    "rulesync_mentions_cursor": true
  },
  "changed": {
    "agent_memories": [
      ".agents/memories/10-repo.md",
      ".agents/memories/20-quality-gates.md",
      ".agents/memories/30-deploy.md"
    ],
    "files": [
      ".agents/memories/10-repo.md",
      ".agents/memories/20-quality-gates.md",
      ".agents/memories/30-deploy.md",
      ".agents/rules/10-repo.md",
      ".agents/rules/20-quality-gates.md",
      ".agents/rules/30-deploy.md",
      ".cursor/rules/00-org.mdc",
      ".cursor/rules/10-repo.mdc",
      ".cursor/rules/20-quality-gates.mdc",
      ".cursor/rules/30-deploy.mdc",
      ".github/workflows/ai-rules-check.yml",
      ".gitignore",
      ".repo-policy.yml",
      ".rulesync/rules/00-org.md",
      ".rulesync/rules/10-repo.md",
      ".rulesync/rules/20-quality-gates.md",
      ".rulesync/rules/30-deploy.md",
      "AGENTS.md",
      "coverage/base.css",
      "coverage/block-navigation.js",
      "coverage/browser.ts.html",
      "coverage/discovery.ts.html",
      "coverage/favicon.png",
      "coverage/find-missing.ts.html",
      "coverage/fix-state.ts.html",
      "coverage/index.html",
      "coverage/index.ts.html",
      "coverage/parser.ts.html",
      "coverage/patch-state.ts.html",
      "coverage/prettify.css",
      "coverage/prettify.js",
      "coverage/scraper.ts.html",
      "coverage/sort-arrow-sprite.png",
      "coverage/sorter.js",
      "coverage/state.ts.html",
      "coverage/test-db.ts.html",
      "coverage/xml-builder.ts.html",
      "coverage/xml-to-sqlite.ts.html",
      "package-lock.json",
      "package.json",
      "rulesync.jsonc"
    ],
    "generated_artifacts": [
      "coverage/base.css",
      "coverage/block-navigation.js",
      "coverage/browser.ts.html",
      "coverage/discovery.ts.html",
      "coverage/favicon.png",
      "coverage/find-missing.ts.html",
      "coverage/fix-state.ts.html",
      "coverage/index.html",
      "coverage/index.ts.html",
      "coverage/parser.ts.html",
      "coverage/patch-state.ts.html",
      "coverage/prettify.css",
      "coverage/prettify.js",
      "coverage/scraper.ts.html",
      "coverage/sort-arrow-sprite.png",
      "coverage/sorter.js",
      "coverage/state.ts.html",
      "coverage/test-db.ts.html",
      "coverage/xml-builder.ts.html",
      "coverage/xml-to-sqlite.ts.html"
    ],
    "risky_deploy_files": [],
    "secretish_files": [],
    "suspicious_agents_paths": []
  },
  "docs": {
    "has_docs_dir": false,
    "has_readme": true,
    "readme_mentions_ai": true,
    "readme_mentions_checks": true,
    "readme_mentions_deploy_or_release": true,
    "readme_mentions_local_dev": true
  },
  "gitignore": {
    "has_coverage": true
  },
  "package": {
    "has_commitlint_dependency": true,
    "has_husky": true,
    "has_lint_staged": true,
    "has_package_json": true,
    "has_rulesync_dependency": true,
    "package_manager": "npm",
    "scripts": {
      "build": "tsc",
      "db:build": "tsx src/xml-to-sqlite.ts",
      "db:seed:local": "wrangler d1 execute nab-api --local --file=output/bible-d1.sql",
      "dev": "wrangler dev src/api.ts",
      "format": "prettier --write .",
      "format:check": "prettier --check .",
      "lint": "eslint",
      "lint:fix": "eslint --fix",
      "prepare": "husky",
      "start": "tsx src/index.ts",
      "test": "vitest run",
      "test:coverage": "vitest run --coverage",
      "typecheck": "tsc --noEmit"
    },
    "tools": [
      "@commitlint/cli",
      "eslint",
      "husky",
      "lint-staged",
      "prettier",
      "rulesync",
      "typescript",
      "vitest"
    ]
  },
  "workflows": {
    "files": [
      ".github/workflows/ai-rules-check.yml",
      ".github/workflows/ci.yml",
      ".github/workflows/deploy.yml",
      ".github/workflows/release-please.yml",
      ".github/workflows/semantic-pull-request.yml"
    ],
    "has_ai_rules_workflow": true,
    "has_release_please": true,
    "has_semantic_pr_workflow": true,
    "mentions_coverage": true,
    "mentions_deploy": true,
    "mentions_lint": true,
    "mentions_test": true,
    "mentions_typecheck": true,
    "workflow_count": 5
  }
}
```