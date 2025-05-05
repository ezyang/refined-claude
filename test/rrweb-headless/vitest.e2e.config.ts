import { defineConfig } from 'vitest/config';

// Determine if we're in debug mode
const isDebugMode = process.env.SUBLIME_DEBUG === '1';

// Check if we're running in a CI or Turbo environment
const isCIorTurbo =
  process.env.CI === 'true' || process.env.TURBO === 'true' || !!process.env.TURBO_TEAM;

export default defineConfig({
  test: {
    environment: 'node',
    include: ['**/*.e2e.test.{js,ts}'],
    // Disable timeout completely in debug mode, otherwise use 2 minutes
    testTimeout: isDebugMode ? 0 : 120000,
    globalSetup: './src/e2e.setup.ts',
    // Use basic reporter when running in CI or Turbo to avoid control character issues
    reporters: isCIorTurbo ? ['basic'] : ['verbose'],
  },
});
