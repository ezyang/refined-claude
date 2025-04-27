import { defineConfig } from 'tsup';

export default defineConfig([
  // Background script (service worker) for MV3 - ES Module format
  {
    entry: ['src/background.ts'],
    format: ['esm'],
    outDir: 'dist',
    clean: false,
    platform: 'browser', // Ensure browser environment
    treeshake: true, // Remove unused code
    dts: {
      resolve: true,
      compilerOptions: {
        composite: false,
        incremental: false,
      },
    },
    sourcemap: false,
    noExternal: ['*'], // Bundle all dependencies
  },

  // Content script for MV3 - IIFE format (no modules)
  {
    entry: ['src/index.ts'],
    format: ['iife'],
    outDir: 'dist',
    clean: false,
    globalName: 'SCContentScript',
    dts: false, // No need for DTS for content script
    sourcemap: false,
  },
]);
