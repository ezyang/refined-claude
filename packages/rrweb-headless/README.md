# @sublime-claude/rrweb-headless

A package for running rrweb replay sessions in a headless browser environment using Playwright. This allows for automated testing and verification of recorded web sessions.

## Features

- Run rrweb recordings in a headless browser
- Control playback speed
- Query DOM state after replay
- Check for the presence of specific elements

## Usage

```typescript
import { runRrwebHeadless } from '@sublime-claude/rrweb-headless';

// Load rrweb events from a file or API
const events = require('./path/to/events.json');

// Run the replay and check for an element
const result = await runRrwebHeadless({
  events,
  playbackSpeed: 4, // 4x speed
  selectors: ['.z-modal'], // Elements to check for
});

console.log(`Modal was ${result.elementExists ? 'found' : 'not found'}`);
```
