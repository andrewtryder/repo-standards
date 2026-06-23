# Security Scanning

## Secret scanning

### Baseline

Copy `templates/workflows/secret-scan.yml` to `.github/workflows/secret-scan.yml` in your repo.

The workflow uses **TruffleHog** to scan pull request diffs for leaked secrets, credentials, and sensitive data.

### Configuration

The template is configured conservatively to reduce false positives:

- `--results=verified` — only flag results TruffleHog can verify (e.g., by checking if a credential is active against a known service).
- `--no-update` — do not auto-update TruffleHog's detection rules during CI (stability).
- `--fail` — exit with non-zero if verified secrets are found.

The scan runs on every pull request. It does not scan the full git history (only the PR diff range).

### Recommended workflow

1. Add the workflow to the repo.
2. Configure branch protection to require the Secret Scan check once it passes consistently.
3. If a false positive is detected, add an allowlist entry. TruffleHog supports path-based exclusions via `--exclude-paths`.
4. Review findings promptly. A verified secret in a PR should block merging.

### What this does NOT cover

- This workflow scans PR diffs only. For historical scans of the full repository, run TruffleHog locally or as a standalone action.
- This does not scan for secrets in issue comments, PR descriptions, or other GitHub metadata.
- This is not a substitute for developer training on secret management.