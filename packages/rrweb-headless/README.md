# rrweb-headless

A tool for running [rrweb](https://github.com/rrweb-io/rrweb) replays in headless or headed browsers using Playwright.

## Usage

### As a library

```typescript
import { runRrwebReplay, loadEventsFromFile } from '@sublime-claude/rrweb-headless';

// Load events from file
const events = await loadEventsFromFile('path/to/events.json');

// Run replay with options
const result = await runRrwebReplay({
  events,
  playbackSpeed: 1.5,
  headless: false,
  timeout: 60000,
  selectors: ['.my-element']
});

console.log(result.selectorResults);
```

### As a CLI debugging tool

The package provides a CLI tool for debugging rrweb recordings:

```bash
# Install the package
npm install @sublime-claude/rrweb-headless

# Run with default settings (headful mode, no timeout)
npx test-rrweb path/to/events.json

# Run with custom settings
npx test-rrweb --speed 2 --timeout 30000 --selector ".my-element" path/to/events.json
```

#### CLI Options

- `--headless`: Run in headless mode (default: headful for debugging)
- `--headful`: Run in headful mode (default for debugging)
- `--speed <number>`: Playback speed multiplier (default: 1)
- `--timeout <ms>`: Timeout in milliseconds (default: 0 = no timeout)
- `--selector <string>`: CSS selector to check (can be used multiple times)
- `--help`, `-h`: Show help information

For debugging purposes, you can use `--timeout 0` to keep the browser open indefinitely (until you press Ctrl+C).

## Installation

```bash
npm install @sublime-claude/rrweb-headless
```

## Package Scripts

- `npm run build`: Build the package
- `npm run dev`: Build in watch mode
- `npm run test-replay`: Run the CLI with default settings
- `npm run test-replay:debug`: Run in debug mode (headful, no timeout)
