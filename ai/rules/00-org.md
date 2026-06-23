---
root: true
targets: ["*"]
description: "Organization-wide engineering rules"
globs: ["*"]
---

# Organization Engineering Rules

## Commits and pull requests

Use Conventional Commits. PR titles must be semantic.

Examples:

- `feat(api): add reading lookup endpoint`
- `fix(worker): handle Cloudflare timeout`
- `docs(readme): clarify local setup`
- `chore(ci): update release workflow`

## Before editing

Inspect existing patterns before adding new abstractions.

## Before finishing

Run the checks listed in `.repo-policy.yml`.

## CI/CD safety

Do not relax linting, typechecking, tests, coverage, or deployment protections to make a change pass.
Do not modify release or deploy workflows unless the task explicitly requires it.

## Secrets

Never commit secrets, tokens, credentials, private keys, `.env` files, or generated production configuration.
