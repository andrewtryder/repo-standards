# TypeScript / JavaScript Rules

Use the repository package manager. Do not change package managers as part of unrelated work.

Node repositories must have a root `.nvmrc` file specifying the Node.js version.
Use `.nvmrc` as the operational source of truth for local development and CI.

Preferred checks:

- `npm run format:check`
- `npm run lint`
- `npm run typecheck`
- `npm test`
- `npm run test:coverage`
- `npm run build`

Use ESLint for linting, TypeScript for typechecking, and Prettier for formatting when configured.
File patterns determine execution: TypeScript/JavaScript checks apply to `*.ts`, `*.tsx`,
`*.js`, `*.jsx`, `*.mjs`, and `*.cjs` files when those files exist.

## Related docs

- `docs/profiles.md`
- `docs/code-quality-standards.md`
- `docs/ai-rules-maintenance.md`
- `docs/detection.md`
- `docs/deployment/cloudflare.md`
