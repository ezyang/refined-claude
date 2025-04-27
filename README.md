# sublime-claude

A TypeScript monorepo following strict TypeScript and ESLint configuration.

## Structure

- `apps/`: Application packages
- `packages/`: Library packages

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

# Format code with Prettier
pnpm format

# Check code formatting without making changes
pnpm format:check
```

### Code Formatting

This project uses Prettier for consistent code formatting across all files, including JSON:

- The root `prettier.config.cjs` contains the global formatting rules
- JSON files get special handling with specific parser settings
- Run `pnpm format` to format all files or `pnpm format:check` to check without fixing
- Individual packages can override formatting by adding their own `.prettierrc` file
- See `prettier.config.example.json` for a sample configuration

## Technologies

- pnpm (package manager)
- Turborepo (monorepo task runner)
- TypeScript (strict configuration)
- ESLint (flat config)
- Prettier
- Vitest (testing)
- tsup (bundling)
