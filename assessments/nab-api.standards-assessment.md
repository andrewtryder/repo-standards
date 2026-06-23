# nab-api Standards Migration Assessment

Generated: `2026-06-23T03:50:02.501434+00:00`
Repo: `/path/to/example-repo`
Standards repo: `/path/to/repo-standards`
Score: **100/100**

## Verdict

Looks ready for review. Remaining items are warnings or follow-up work.

## Blockers

- None detected

## Warnings

- None detected

## AI/editor rules

- `has_repo_policy`: `True`
- `has_rulesync_config`: `True`
- `has_rulesync_rules_dir`: `True`
- `has_agents_md`: `True`
- `has_cursor_rules`: `True`
- `has_antigravity_rules`: `True`
- `rulesync_mentions_agentsmd`: `True`
- `rulesync_mentions_cursor`: `True`
- `rulesync_mentions_antigravity`: `True`
- `rule_files`: `['.rulesync/rules/00-org.md', '.rulesync/rules/10-repo.md', '.rulesync/rules/20-quality-gates.md', '.rulesync/rules/30-deploy.md']`

## Workflows

- `workflow_count`: `5`
- `files`: `['.github/workflows/ai-rules-check.yml', '.github/workflows/ci.yml', '.github/workflows/deploy.yml', '.github/workflows/release-please.yml', '.github/workflows/semantic-pull-request.yml']`
- `has_ai_rules_workflow`: `True`
- `has_semantic_pr_workflow`: `True`
- `has_release_please`: `True`
- `mentions_lint`: `True`
- `mentions_typecheck`: `True`
- `mentions_test`: `True`
- `mentions_coverage`: `True`
- `mentions_deploy`: `True`

## Package state

- `has_package_json`: `True`
- `package_manager`: `npm`
- `has_rulesync_dependency`: `True`
- `has_commitlint_dependency`: `True`
- `has_husky`: `True`
- `has_lint_staged`: `True`
- `tools`: `['@commitlint/cli', 'eslint', 'husky', 'lint-staged', 'prettier', 'rulesync', 'typescript', 'vitest']`

## Python state

- `has_pyproject`: `False`
- `has_requirements`: `False`
- `has_pre_commit`: `False`
- `has_ruff_config`: `False`
- `mentions_pytest`: `False`
- `mentions_coverage`: `False`

## Docs

- `has_readme`: `True`
- `has_docs_dir`: `False`
- `readme_mentions_local_dev`: `True`
- `readme_mentions_checks`: `True`
- `readme_mentions_deploy_or_release`: `True`
- `readme_mentions_ai`: `True`

## Package scripts

- `build`: `tsc`
- `db:build`: `tsx src/xml-to-sqlite.ts`
- `db:seed:local`: `wrangler d1 execute nab-api --local --file=output/bible-d1.sql`
- `dev`: `wrangler dev src/api.ts`
- `format`: `prettier --write .`
- `format:check`: `prettier --check .`
- `lint`: `eslint`
- `lint:fix`: `eslint --fix`
- `prepare`: `husky`
- `start`: `tsx src/index.ts`
- `test`: `vitest run`
- `test:coverage`: `vitest run --coverage`
- `typecheck`: `tsc --noEmit`

## Changed files

- `.agents/memories/`
- `.agents/rules/10-repo.md`
- `.agents/rules/20-quality-gates.md`
- `.agents/rules/30-deploy.md`
- `.cursor/`
- `.github/workflows/ai-rules-check.yml`
- `.repo-policy.yml`
- `.rulesync/`
- `AGENTS.md`
- `agents/rules/conventional-commits.md`
- `coverage/browser.ts.html`
- `coverage/discovery.ts.html`
- `coverage/find-missing.ts.html`
- `coverage/fix-state.ts.html`
- `coverage/index.html`
- `coverage/index.ts.html`
- `coverage/parser.ts.html`
- `coverage/patch-state.ts.html`
- `coverage/scraper.ts.html`
- `coverage/state.ts.html`
- `coverage/test-db.ts.html`
- `coverage/xml-builder.ts.html`
- `coverage/xml-to-sqlite.ts.html`
- `package-lock.json`
- `package.json`
- `rulesync.jsonc`

## Command results

### PASS: `npm ci`

```txt
> nab-api@1.0.0 prepare
> husky


added 612 packages, and audited 613 packages in 11s

176 packages are looking for funding
  run `npm fund` for details

7 vulnerabilities (1 low, 2 moderate, 4 high)

To address issues that do not require attention, run:
  npm audit fix

To address all issues (including breaking changes), run:
  npm audit fix --force

Run `npm audit` for details.
```

```txt
npm warn deprecated inflight@1.0.6: This module is not supported, and leaks memory. Do not use it. Check out lru-cache if you want a good and tested way to coalesce async requests by a key value, which is much more comprehensive and powerful.
npm warn deprecated rimraf@3.0.2: Rimraf versions prior to v4 are no longer supported
npm warn deprecated whatwg-encoding@3.1.1: Use @exodus/bytes instead for a more spec-conformant and faster implementation
npm warn deprecated glob@7.2.3: Old versions of glob are not supported, and contain widely publicized security vulnerabilities, which have been fixed in the current version. Please update. Support for old versions may be purchased (at exorbitant rates) by contacting i@izs.me
npm warn deprecated koa-router@14.0.0: Please use @koa/router instead, starting from v9! 
npm warn allow-scripts 8 packages have install scripts not yet covered by allowScripts:
npm warn allow-scripts   esbuild@0.28.0 (postinstall: node install.js)
npm warn allow-scripts   fsevents@2.3.2 (install: (install scripts present))
npm warn allow-scripts   sharp@0.34.5 (install: node install/check.js || npm run build)
npm warn allow-scripts   tldjs@2.3.2 (postinstall: node ./bin/postinstall.js)
npm warn allow-scripts   fsevents@2.3.3 (install: (install scripts present))
npm warn allow-scripts   fsevents@2.3.3 (install: (install scripts present))
npm warn allow-scripts   workerd@1.20260426.1 (postinstall: node install.js)
npm warn allow-scripts   esbuild@0.27.3 (postinstall: node install.js)
npm warn allow-scripts
npm warn allow-scripts Run `npm approve-scripts --allow-scripts-pending` to review, or `npm approve-scripts <pkg>` to allow.
```

### PASS: `npm run lint`

```txt
> nab-api@1.0.0 lint
> eslint


/path/to/example-repo/src/api.ts
   72:19  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
   98:19  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  151:43  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  152:47  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  154:39  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  166:43  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  178:53  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  193:19  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  223:19  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

/path/to/example-repo/src/browser.ts
   70:9   warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  241:21  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

/path/to/example-repo/src/find-missing.ts
  12:45  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

/path/to/example-repo/src/fix-state.ts
  27:43  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

/path/to/example-repo/src/scraper.ts
  159:17  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

/path/to/example-repo/src/state.ts
  42:21  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  63:19  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

/path/to/example-repo/src/test-db.ts
    9:18  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
   22:19  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any
  233:19  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

/path/to/example-repo/src/xml-to-sqlite.ts
  303:19  warning  Unexpected any. Specify a different type  @typescript-eslint/no-explicit-any

✖ 20 problems (0 errors, 20 warnings)
```

### PASS: `npm run typecheck`

```txt
> nab-api@1.0.0 typecheck
> tsc --noEmit
```

### PASS: `npm run test`

```txt
> nab-api@1.0.0 test
> vitest run


[1m[30m[46m RUN [49m[39m[22m [36mv4.1.8 [39m[90m/path/to/example-repo[39m

 [32m✓[39m dist/parser.test.js [2m([22m[2m2 tests[22m[2m)[22m[32m 13[2mms[22m[39m
 [32m✓[39m src/parser.test.ts [2m([22m[2m2 tests[22m[2m)[22m[32m 12[2mms[22m[39m

[2m Test Files [22m [1m[32m2 passed[39m[22m[90m (2)[39m
[2m      Tests [22m [1m[32m4 passed[39m[22m[90m (4)[39m
[2m   Start at [22m 23:49:58
[2m   Duration [22m 776ms[2m (transform 112ms, setup 0ms, import 1.28s, tests 25ms, environment 0ms)[22m
```

### PASS: `npm run test:coverage`

```txt
> nab-api@1.0.0 test:coverage
> vitest run --coverage


[1m[30m[46m RUN [49m[39m[22m [36mv4.1.8 [39m[90m/path/to/example-repo[39m
      [2mCoverage enabled with [22m[33mv8[39m

 [32m✓[39m src/parser.test.ts [2m([22m[2m2 tests[22m[2m)[22m[32m 15[2mms[22m[39m
 [32m✓[39m dist/parser.test.js [2m([22m[2m2 tests[22m[2m)[22m[32m 15[2mms[22m[39m

[2m Test Files [22m [1m[32m2 passed[39m[22m[90m (2)[39m
[2m      Tests [22m [1m[32m4 passed[39m[22m[90m (4)[39m
[2m   Start at [22m 23:49:59
[2m   Duration [22m 766ms[2m (transform 109ms, setup 0ms, import 972ms, tests 30ms, environment 0ms)[22m

[34m % [39m[2mCoverage report from [22m[33mv8[39m
------------------|---------|----------|---------|---------|--------------------
File              | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s  
------------------|---------|----------|---------|---------|--------------------
All files         |    8.01 |     8.64 |    9.61 |    8.29 |                    
 browser.ts       |    2.35 |        0 |       0 |     2.4 | 13,25-250          
 discovery.ts     |       0 |        0 |       0 |       0 | 8-120              
 find-missing.ts  |       0 |        0 |     100 |       0 | 4-27               
 fix-state.ts     |       0 |        0 |       0 |       0 | 4-72               
 index.ts         |       0 |        0 |       0 |       0 | 6-67               
 parser.ts        |   22.07 |    18.96 |    62.5 |   22.97 | ...121-123,229-748 
 patch-state.ts   |       0 |        0 |     100 |       0 | 4-23               
 scraper.ts       |       0 |        0 |       0 |       0 | 25-167             
 state.ts         |       0 |        0 |       0 |       0 | 28-116             
 test-db.ts       |       0 |        0 |       0 |       0 | 5-250              
 xml-builder.ts   |       0 |        0 |       0 |       0 | 10-101             
 xml-to-sqlite.ts |       0 |        0 |       0 |       0 | 7-311              
------------------|---------|----------|---------|---------|--------------------
```

### PASS: `npm run build`

```txt
> nab-api@1.0.0 build
> tsc
```

### PASS: `npx rulesync generate`

```txt
Written 2 rules
    AGENTS.md
    AGENTS.md
🎉 All done! Written 2 file(s) total (2 rules)
```

### PASS: `git diff --check`


## Recommendations

- None

## Standards feedback

- No repo-standards blueprint changes suggested by this assessment.