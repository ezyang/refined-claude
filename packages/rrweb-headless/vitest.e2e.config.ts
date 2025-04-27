import { defineConfig } from 'vitest/config';

// Determine if we're in debug mode
const isDebugMode = process.env.SUBLIME_DEBUG === '1';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['**/*.e2e.test.{js,ts}'],
    // Disable timeout completely in debug mode, otherwise use 2 minutes
    testTimeout: isDebugMode ? 0 : 120000,
    globalSetup: './src/e2e.setup.ts',
    // Don't run tests in parallel to avoid browser conflicts
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: true,
      },
    },
  },
});
