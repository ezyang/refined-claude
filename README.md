# sublime-claude

A TypeScript monorepo following strict TypeScript and ESLint configuration.

## Structure

- `apps/`: Application packages
- `packages/`: Library packages
  - `utils/`: Utility functions

## Development

This project uses pnpm workspaces and Turborepo for monorepo management.

### Setup

```bash
# Install dependencies
pnpm install

# Build all packages
pnpm build

# Run tests
pnpm test

# Lint code
pnpm lint

# Type check
pnpm typecheck
```

## Technologies

- pnpm (package manager)
- Turborepo (monorepo task runner)
- TypeScript (strict configuration)
- ESLint (flat config)
- Prettier
- Vitest (testing)
- tsup (bundling)
