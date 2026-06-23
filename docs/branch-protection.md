# Branch Protection: Required Checks

After migrating a repo to the standard, configure branch protection rules on the default branch (typically `main`) to require the following checks before merging.

## Required checks

| Check name (workflow) | Required | Notes |
|---|---|---|
| **Semantic Pull Request** | Always | Validates PR title follows Conventional Commits. |
| **AI Rules** | Always | Fails if generated AI/editor files are out of sync with `.rulesync/` source. |
| **CI** | Always | Runs install, lint, test, coverage, build for the repo profile. |
| **Docs** | Always | Validates required docs exist and README covers required concepts. |
| **Docs / AI Rule Sync** | Recommended | Warns when docs/templates/profiles change without AI rule source updates. Promote to required after the rule stabilizes. |
| **Secret Scan** | Recommended | Scans PR diffs for verified secrets using TruffleHog. Add once it passes consistently. |
| **Deploy check** | When deploy workflow is configured | Ensures deployment is not broken by standards changes. Deploy workflows are not modified by standard migration. |
| **Release check** | When Release Please is configured | Ensures release PR creation is working. Release workflows are not modified by standard migration. |

## How to configure

1. Go to the repo's Settings > Branches > Add branch protection rule.
2. Set "Branch name pattern" to `main`.
3. Enable "Require status checks to pass before merging".
4. Add the checks listed above as required status checks.
5. Enable "Require branches to be up to date" with the CI check.
6. Optionally enable "Include administrators" to ensure the rules apply universally.

## Notes

- Check names in GitHub appear as the workflow `name` field. Verify the exact casing (e.g., "Semantic Pull Request", not "semantic-pull-request").
- The standard migration PR itself should only add workflows, `.repo-policy.yml`, rulesync config, and AI/editor generated files. Deploy and release workflows should remain untouched.
- Branch protection can be configured before or after the migration PR is merged. Configuring it before ensures the migration PR itself passes all required checks.
- Secret Scan is listed as "Recommended" rather than "Always" because not all repos may have it configured yet. Once it passes consistently, promote it to required.

## Blocker vs warning distinction for branch protection

Branch protection rules enforce only required checks. The following are handled **outside** branch protection:

| Category | Action |
|---|---|
| Blockers detected by assessor | Must be resolved before the PR can be considered ready |
| Warnings / follow-up items | Tracked as issues or follow-up PRs, not blocking |
| Deleted coverage artifacts (`D coverage/...`) | Acceptable cleanup when `coverage/` is in `.gitignore` |
| Low coverage, ESLint warnings, npm audit | Documented tech debt, not merge blockers |
| Missing `.nvmrc`, Dependabot, secret scan | Recommended but not yet blocking checks |