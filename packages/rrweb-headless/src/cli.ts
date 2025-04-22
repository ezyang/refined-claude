#!/usr/bin/env node

import { runRrwebReplay, loadEventsFromFile } from './index.js';
import * as path from 'path';
import * as fs from 'fs/promises';

// Parse command line arguments
const args = process.argv.slice(2);
let jsonFilePath: string | null = null;
let headless = false; // Default to headful mode for debugging
let playbackSpeed = 1;
let timeout = 0; // Default to no timeout for debugging (browser stays open)
let selectors: string[] = [];

// Helper to check if a file exists
async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

// Parse arguments
function parseArgs() {
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--headless') {
      headless = true;
    } else if (arg === '--headful') {
      headless = false;
    } else if (arg === '--speed' && i + 1 < args.length) {
      const nextArg = args[i + 1];
      if (nextArg) {
        ++i;
        playbackSpeed = parseFloat(nextArg);
        if (isNaN(playbackSpeed) || playbackSpeed <= 0) {
          playbackSpeed = 1;
        }
      }
    } else if (arg === '--timeout' && i + 1 < args.length) {
      const nextArg = args[i + 1];
      if (nextArg) {
        ++i;
        timeout = parseInt(nextArg, 10);
        if (isNaN(timeout) || timeout < 0) {
          timeout = 0;
        }
      }
    } else if (arg === '--selector' && i + 1 < args.length) {
      const nextArg = args[i + 1];
      if (nextArg) {
        ++i;
        selectors.push(nextArg);
      }
    } else if (arg === '--help' || arg === '-h') {
      printHelp();
      process.exit(0);
    } else if (arg && !arg.startsWith('--') && jsonFilePath === null) {
      // Assume it's the JSON file path
      jsonFilePath = arg;
    }
  }

  if (!jsonFilePath) {
    console.error('Error: No JSON file specified');
    printHelp();
    process.exit(1);
  }
}

// Print help information
function printHelp() {
  console.log(`
  rrweb-headless - Debug Tool for rrweb Replay

  Usage:
    test-rrweb [options] <events.json>

  Options:
    --headless           Run in headless mode (default: headful)
    --headful            Run in headful mode (default)
    --speed <number>     Playback speed multiplier (default: 1)
    --timeout <ms>       Timeout in milliseconds (default: 0 = no timeout)
    --selector <string>  CSS selector to check (can be used multiple times)
    --help, -h           Show this help information

  Examples:
    test-rrweb events.json
    test-rrweb --speed 2 events.json
    test-rrweb --timeout 60000 --selector ".my-element" events.json
  `);
}

// Main function to run the replay
async function main() {
  parseArgs();

  if (!jsonFilePath) {
    return;
  }

  // Resolve relative paths
  const resolvedPath = path.resolve(process.cwd(), jsonFilePath);

  // Check if file exists
  if (!(await fileExists(resolvedPath))) {
    console.error(`Error: File not found: ${resolvedPath}`);
    process.exit(1);
  }

  const isDebugMode = process.env.SUBLIME_DEBUG === '1';
  console.log(`Loading events from: ${resolvedPath}`);
  console.log(`Mode: ${headless ? 'headless' : 'headful'}${isDebugMode ? ' (debug mode)' : ''}`);
  console.log(`Playback speed: ${playbackSpeed}x`);
  console.log(`Timeout: ${timeout === 0 || isDebugMode ? 'none (browser will stay open)' : timeout + 'ms'}`);

  if (selectors.length > 0) {
    console.log('Checking for selectors:');
    selectors.forEach(selector => console.log(`  - ${selector}`));
  }

  try {
    // Load events from the JSON file
    const events = await loadEventsFromFile(resolvedPath);

    if (!events || !Array.isArray(events) || events.length === 0) {
      console.error('Error: No valid events found in the file');
      process.exit(1);
    }

    console.log(`Loaded ${events.length} events`);

    // Run the replay
    const result = await runRrwebReplay({
      events,
      playbackSpeed,
      headless,
      timeout,
      selectors
    });

    // When timeout is 0 or debug mode is on, this code won't be reached until the process is killed
    if (timeout !== 0 && process.env.SUBLIME_DEBUG !== '1') {
      if (result.error) {
        console.error('\nReplay encountered an error:', result.error);
        process.exit(1);
      } else if (result.replayCompleted) {
        console.log('\nReplay completed successfully! ✓');
      } else {
        console.warn('\nReplay may not have fully completed before timeout.');
      }

      if (selectors.length > 0) {
        console.log(`All selectors found: ${result.elementExists ? 'Yes ✓' : 'No ✗'}`);
      }
    }
  } catch (error) {
    console.error('Error during replay:', error);
    process.exit(1);
  }
}

// Run the main function
main().catch(err => {
  console.error('Unhandled error:', err);
  process.exit(1);
});
