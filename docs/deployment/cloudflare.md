# Cloudflare deployment

Guidance for repositories deployed to Cloudflare (typically Workers via Wrangler).

## Detection evidence

The detector recognizes Cloudflare when it finds:

- `wrangler.toml`, `wrangler.json`, or `wrangler.jsonc`
- `package.json` scripts mentioning `wrangler` or `cloudflare`
- `.github/workflows/*.yml` mentioning `wrangler` or `cloudflare`

## Recommended profile

Cloudflare Workers commonly use the **`typescript-cloudflare-worker`** profile.

```bash
python3 /path/to/repo-standards/scripts/detect_repo_standard.py --repo .
```

## What should remain repo-specific

During and after first migration, keep repo-specific:

- **Production deploy workflow** — Wrangler deploy steps, environments, and triggers
- **Wrangler configuration** — `wrangler.toml` / `wrangler.jsonc` bindings, routes, compatibility flags
- **Cloudflare secrets** — stored in Cloudflare, not in the repository
- **Custom build steps** — bundler config, asset uploads, Durable Objects migrations

The standards repo provides CI and governance templates, not a replacement deploy pipeline.

## What standards still apply

Even with repo-specific deploy workflows, adopt:

- `.repo-policy.yml` with `typescript-cloudflare-worker` profile
- AI/editor rules via Rulesync
- Semantic PR, AI rules check, docs check, secret scan workflows
- Dependabot
- `.gitignore` using `templates/gitignore/cloudflare-worker.gitignore`
- `.env.example` with comments that production secrets belong in Wrangler/Cloudflare

## First migration PR — do not change

- Do **not** alter production deploy behavior
- Do **not** modify `wrangler.toml` bindings or routes for standards adoption
- Do **not** commit Wrangler secrets or API tokens
- Do **not** replace existing deploy workflows — add standards workflows alongside them

## Suggested follow-up improvements

After the first migration PR merges:

1. Pin Wrangler version in CI and document in `.repo-policy.yml` commands
2. Add deploy workflow documentation to `README.md`
3. Consider reusable `node-ci` workflow from repo-standards
4. Review `.env.example.cloudflare` template for missing variables
5. Evaluate devcontainer template at `templates/devcontainer/cloudflare-worker/`

## Secrets

Keep Wrangler secrets in Cloudflare (via `wrangler secret put` or the Cloudflare dashboard). Never commit secrets to the repository or `.env` files.
