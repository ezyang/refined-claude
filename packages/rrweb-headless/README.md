# rrweb-headless

A tool for running [rrweb](https://github.com/rrweb-io/rrweb) replays in headless or headed browsers using Playwright. This allows you to visualize recorded user sessions with full webpage content and mouse movements.

## Features

- Run rrweb replays headlessly or with a visible browser
- View complete webpage content alongside mouse movements and interactions
- Set playback speed for faster analysis
- Check for the existence of specific elements using CSS selectors
- Built-in debugging tools and visualizations

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
  headless: false, // Set to false to see the full replay with webpage content
  timeout: 60000,
  selectors: ['.my-element']
});

console.log(result.selectorResults);
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
