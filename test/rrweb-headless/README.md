# rrweb-headless

A tool for running [rrweb](https://github.com/rrweb-io/rrweb) replays in headless or headed browsers using Playwright. This allows you to visualize recorded user sessions with full webpage content and mouse movements.

## Features

- Run rrweb replays headlessly or with a visible browser
- View complete webpage content alongside mouse movements and interactions
- Set playback speed for faster analysis
- Built-in debugging tools and visualizations
- Support for persistent browser profiles with user data directories
- Explicit browser channel selection for consistent browser versions

## Usage

### As a library

```typescript
import { runRrwebReplay, loadEventsFromFile } from '@refined-claude/rrweb-headless';

// Load events from file
const events = await loadEventsFromFile('path/to/events.json');

// Run replay with options
const result = await runRrwebReplay({
  events,
  playbackSpeed: 1.5,
  headless: false, // Set to false to see the full replay with webpage content
  timeout: 60000,
  // Use persistent browser profile (optional)
  userDataDir: path.resolve(__dirname, '.playwright-data'),
  // Explicitly use Chromium channel for consistent browser version
  channel: 'chromium',
});

console.log(result.elementExists); // Whether all specified elements exist
```

### Troubleshooting Webpage Rendering

If you're not seeing the actual webpage content (only mouse movements):

1. Make sure your recording includes full snapshots (DOM captures)
2. Use `headless: false` to view the replay in a browser window
3. Check the console logs for warnings about missing snapshots
4. For debugging, use the CLI tool with `--timeout 0` to keep the browser open

### As a CLI debugging tool

The package provides a CLI tool for debugging rrweb recordings:

```bash
# Install the package
npm install @refined-claude/rrweb-headless

# Run with default settings (headful mode, no timeout)
npx test-rrweb path/to/events.json

# Run with custom settings
npx test-rrweb --speed 2 --timeout 30000 --selector ".my-element" path/to/events.json

# Run in debug mode with devtools console open
SUBLIME_DEBUG=1 npx test-rrweb path/to/events.json
```

#### CLI Options

- `--headless`: Run in headless mode (default: headful for debugging)
- `--headful`: Run in headful mode (default for debugging)
- `--speed <number>`: Playback speed multiplier (default: 1)
- `--timeout <ms>`: Timeout in milliseconds (default: 0 = no timeout)
- `--selector <string>`: CSS selector to check (can be used multiple times)
- `--user-data-dir <path>`: Path to user data directory for persistent browser profile
- `--channel <string>`: Browser channel to use (chromium, chrome, msedge, etc.)
- `--help`, `-h`: Show help information

#### Environment Variables

- `SUBLIME_DEBUG=1`: Enable debug mode - opens a headful browser with devtools console open and keeps the browser open indefinitely

For debugging purposes, you can use `--timeout 0` to keep the browser open indefinitely (until you press Ctrl+C), or set the `SUBLIME_DEBUG=1` environment variable to automatically open a browser with devtools.

### Browser Profiles

#### Fresh Profiles for Test Parallelization

For testing, we recommend creating a fresh browser profile for each test run. This approach:

- Ensures test isolation (no state leakage between tests)
- Enables test parallelization (each test uses a unique profile)
- Reloads extensions and background scripts each time

```typescript
// Create a unique temporary profile for this test run
const userDataDir = path.resolve(
  __dirname,
  '.tmp-playwright',
  `test-run-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
);

// Ensure the directory exists
await fs.mkdir(userDataDir, { recursive: true });

// Use the fresh profile
const result = await runRrwebReplay({
  events,
  userDataDir: userDataDir,
  channel: 'chromium',
});

// Clean up the temporary directory afterward
await fs.rm(userDataDir, { recursive: true, force: true });
```

#### Persistent Browser Profiles

For debugging, you can use persistent browser profiles to maintain state between replay sessions:

```typescript
// Create a persistent profile
const userDataDir = path.resolve(__dirname, '.playwright-data');

// Ensure the directory exists
await fs.mkdir(userDataDir, { recursive: true });

// Use the persistent profile
const result = await runRrwebReplay({
  events,
  userDataDir: userDataDir,
  channel: 'chromium', // Explicitly use Chromium channel
});
```

Benefits of persistent profiles for debugging:

- Browser state (cookies, local storage, etc.) is preserved between sessions
- Faster startup time for subsequent sessions
- Extensions state is maintained

### Browser Channel Selection

You can specify which browser channel to use:

```typescript
const result = await runRrwebReplay({
  events,
  // Use specific browser channel
  channel: 'chromium', // 'chrome', 'msedge', etc.
});
```

Using the explicit channel provides:

- Consistent browser version across environments
- Better compatibility with certain extensions
- More predictable behavior in continuous integration

## Installation

```bash
npm install @refined-claude/rrweb-headless
```

## Package Scripts

- `npm run build`: Build the package
- `npm run dev`: Build in watch mode
- `npm run test-replay`: Run the CLI with default settings
- `npm run test-replay:debug`: Run in debug mode (headful, no timeout)
- `npm run test-replay:devtools`: Run with SUBLIME_DEBUG=1 to open devtools console
