import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts', 'src/cli.ts'],
  format: ['esm', 'cjs'],
  dts: true,
  splitting: false,
  sourcemap: false,
  clean: true,
  // Use custom tsconfig that disables incremental build
  tsconfig: './tsconfig.build.json',
  treeshake: true,
});
