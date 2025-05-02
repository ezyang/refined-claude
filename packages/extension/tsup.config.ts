import { defineConfig } from 'tsup';
import { copyFileSync } from 'fs';
import path from 'path';

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
    publicDir: 'public', // Copy static assets from public directory
    esbuildOptions(options) {
      options.assetNames = 'assets/[name]';
    },
    async onSuccess() {
      // Copy manifest.json to dist
      copyFileSync(
        path.resolve(__dirname, 'src/manifest.json'),
        path.resolve(__dirname, 'dist/manifest.json')
      );

      // Copy popup.html to dist
      copyFileSync(
        path.resolve(__dirname, 'src/popup.html'),
        path.resolve(__dirname, 'dist/popup.html')
      );

      // Copy popup.js to dist
      copyFileSync(
        path.resolve(__dirname, 'src/popup.js'),
        path.resolve(__dirname, 'dist/popup.js')
      );
    },
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
    publicDir: 'public', // Share the same public directory
  },
]);
