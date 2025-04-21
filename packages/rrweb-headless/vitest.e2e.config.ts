import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['**/*.e2e.test.{js,ts}'],
    testTimeout: 120000, // 2 minutes timeout for e2e tests
    globalSetup: './src/e2e.setup.ts',
    // Don't run tests in parallel to avoid browser conflicts
    pool: 'forks',
    poolOptions: {
      forks: {
        singleFork: true
      }
    }
  }
});
