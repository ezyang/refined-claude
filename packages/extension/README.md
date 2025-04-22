# Sublime Claude Chrome Extension

A Chrome extension that automatically clicks the "Allow for this chat" button in modal dialogs with `.z-modal` class.

## Features

- Detects `.z-modal` elements on the page
- Automatically clicks "Allow for this chat" buttons within modals
- Special testing mode for use with rrweb replay environments

## Development

```bash
# Install dependencies
pnpm install

# Build the extension
pnpm build

# Run tests
pnpm test
```

## Usage in Tests

This extension can be loaded in Playwright tests to automatically handle modal dialogs during rrweb replays. The extension has special detection for rrweb replay environments and will create DOM markers instead of actually clicking buttons when in test mode.

```typescript
import { runRrwebReplay } from '@sublime-claude/rrweb-headless';
import path from 'path';

// Path to extension
const extensionPath = path.resolve(__dirname, '../../extension/dist');

// Run replay with extension
const result = await runRrwebReplay({
  events: testEvents,
  chromiumArgs: [
    `--disable-extensions-except=${extensionPath}`,
    `--load-extension=${extensionPath}`
  ]
});

// Check if button was clicked
const buttonClicked = await result.page?.evaluate(() => {
  return document.getElementById('allow-button-clicked-marker') !== null;
});
```

## Extension Structure

- `src/manifest.json` - Chrome extension manifest
- `src/index.ts` - Content script that runs on pages
- `src/background.ts` - Background script for extension initialization
- `src/utils/rrwebPlayer.ts` - Utilities for testing with rrweb
