---
targets: ["*"]
description: "TypeScript and JavaScript standards"
globs: ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.mjs", "**/*.cjs"]
---

# TypeScript / JavaScript Rules

Use the repository package manager. Do not change package managers as part of unrelated work.

Preferred checks:

- `npm run format:check`
- `npm run lint`
- `npm run typecheck`
- `npm test`
- `npm run test:coverage`
- `npm run build`

Use ESLint for linting, TypeScript for typechecking, and Prettier for formatting when configured.
