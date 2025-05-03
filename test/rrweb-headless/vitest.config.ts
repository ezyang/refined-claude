import { defineConfig } from 'vitest/config';

// Check if we're running in a CI or Turbo environment
const isCIorTurbo =
  process.env.CI === 'true' || process.env.TURBO === 'true' || !!process.env.TURBO_TEAM;

export default defineConfig({
  test: {
    environment: 'node',
    includeSource: ['src/**/*.{js,ts}'],
    // Use basic reporter when running in CI or Turbo to avoid control character issues
    reporters: isCIorTurbo ? ['basic'] : ['verbose'],
  },
});
