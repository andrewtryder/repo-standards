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
6. **Add governance files**: `CONTRIBUTING.md`, `LICENSE` (or `LICENSE.md`), `.github/PULL_REQUEST_TEMPLATE.md`. Set `visibility` and `license` in `.repo-policy.yml`.
7. **Add semantic PR check** (`templates/workflows/semantic-pull-request.yml`).
8. **Add AI rules check** (`templates/workflows/ai-rules-check.yml`).
9. **Preserve existing deploy behavior** -- do not modify deploy/release workflows unless explicitly required.
10. **Run coverage checks**: Run the coverage command for the repo. Remove the local generated `coverage/` directory after running. Ensure `coverage/` is in `.gitignore`. Stage deletion of previously tracked coverage files if they exist (these will appear as `D coverage/...` which is acceptable cleanup).
11. **Check for non-dot `agents/` paths**:
    ```sh
    find agents -maxdepth 3 -type f -print 2>/dev/null || true
    ```
    Expected output should be empty. If it is not, verify those paths are intentional and documented.
12. **Run the assessment script** (`scripts/assess_repo_standards.py`) and resolve any blockers.
13. **Configure branch protection** rules with required checks (see `docs/branch-protection.md`).

## Pilot

Start with low-risk repositories that exercise the standard without complex deployment or release behavior.

1. Example TypeScript library or worker
2. Example Python integration or service

## Next batch

Expand to repositories with moderate CI, dependency, or deployment needs after the pilot repositories pass assessment cleanly.

3. Example frontend or backend application
4. Example Cloudflare Worker
5. Example Python service
6. Example Home Assistant integration
7. Example scheduled job or automation repo
8. Example API service

## Later / special

Migrate higher-risk or unusual repositories only after the standard is proven in simple Node and Python repos.

9. Example monorepo
10. Example multi-language service
11. Example repo with custom release automation
12. Example repo with complex deployment rules
13. Example repo with legacy CI constraints
