# Suggested Migration Order

## What "migration" means

Migrating a repo to this standard means performing the following steps:

1. **Add `.repo-policy.yml`** defining the repo profile, commands, quality gates, release, and deploy settings.
2. **Add `.nvmrc`** (for Node repos) with the project's Node.js version.
3. **Add rulesync configuration and source rules** (`.rulesync/rules/*.md`, `rulesync.jsonc`).
4. **Generate AI/editor outputs** using `npx rulesync generate`. Verify all targets produce expected files:
   ```sh
   find AGENTS.md .cursor .agents .rulesync -maxdepth 4 -type f -print | sort
   ```
   Commit generated files: `AGENTS.md`, `.cursor/rules/*.mdc`, `.agents/rules/*.md`, and `.agents/memories/*.md` (if `antigravity-ide` target is enabled).
5. **Add Dependabot** by copying `templates/dependabot.yml` to `.github/dependabot.yml`.
6. **Add semantic PR check** (`templates/workflows/semantic-pull-request.yml`).
7. **Add AI rules check** (`templates/workflows/ai-rules-check.yml`).
8. **Preserve existing deploy behavior** -- do not modify deploy/release workflows unless explicitly required.
9. **Run coverage checks**: Run the coverage command for the repo. Remove the local generated `coverage/` directory after running. Ensure `coverage/` is in `.gitignore`. Stage deletion of previously tracked coverage files if they exist (these will appear as `D coverage/...` which is acceptable cleanup).
10. **Check for non-dot `agents/` paths**:
    ```sh
    find agents -maxdepth 3 -type f -print 2>/dev/null || true
    ```
    Expected output should be empty. If it is not, verify those paths are intentional and documented.
11. **Run the assessment script** (`scripts/assess_repo_standards_migration_v3.py`) and resolve any blockers.
12. **Configure branch protection** rules with required checks (see `docs/branch-protection.md`).

## Pilot

1. nab-api
2. ha-myq-garage

## Next batch

3. cloudflare-hero
4. catholic-mass-readings
5. gdrive-portfolio
6. dailyreadings-api
7. cloudflare-worker-pdf-maker
8. myq-garage-worker
9. unifi-ddns
10. sunsethue-helper

## Later / special

11. anteverbum
12. esotericvernacular
13. ha-iguardstove
14. ha-smart-oil-gauge
15. telegram-stock-price-bot
16. fb-watcher
17. fractio-verbi
18. spiritbound-analytics

Mixed/special repos should be migrated only after the standard is proven in simple Node and Python repos.