import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'happy-dom',
    globals: true,
    include: ['test/**/*.test.ts'],
    // Enable parallel test execution
    pool: 'threads',
    poolOptions: {
      threads: {
        // Use number of available CPUs for maximum parallelization
        // You can adjust this number based on your needs
        maxThreads: Math.max(1, require('os').cpus().length - 1),
        minThreads: 1,
      },
    },
  },
});
