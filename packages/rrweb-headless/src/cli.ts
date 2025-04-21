#!/usr/bin/env node

import { runRrwebHeadless, loadEventsFromFile } from './index';
import path from 'path';

// Parse command line arguments
function parseArgs() {
  const args = process.argv.slice(2);
  const options: {
    testDataPath: string;
    selectors: string[];
    headless: boolean;
    speed: number;
    timeout: number;
    debug: boolean;
  } = {
    testDataPath: '../../testdata/approve-tool.json',
    selectors: ['.z-modal'],
    headless: true,
    speed: 4,
    timeout: 60000,
    debug: false
  };

  // Very simple argument parsing
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--headful' || arg === '--no-headless') {
      options.headless = false;
    } else if (arg === '--debug') {
      options.debug = true;
    } else if (arg === '--speed' && i + 1 < args.length) {
      options.speed = Number(args[++i]);
    } else if (arg === '--timeout' && i + 1 < args.length) {
      options.timeout = Number(args[++i]);
    } else if (arg === '--selector' && i + 1 < args.length) {
      options.selectors.push(args[++i]);
    } else if (!arg.startsWith('--')) {
      options.testDataPath = arg;
    }
  }

  return options;
}

async function main() {
  console.log('Running rrweb headless test...');

  try {
    const options = parseArgs();
    const absolutePath = path.resolve(process.cwd(), options.testDataPath);

    console.log(`Using test data from: ${absolutePath}`);
    console.log(`Playback speed: ${options.speed}x`);
    console.log(`Headless mode: ${options.headless}`);
    console.log(`Checking selectors: ${options.selectors.join(', ')}`);

    // Load events from file
    const events = await loadEventsFromFile(absolutePath);
    console.log(`Loaded ${events.length} events from file`);

    if (options.debug) {
      console.log('First event:', JSON.stringify(events[0], null, 2));
      console.log('Last event:', JSON.stringify(events[events.length - 1], null, 2));
    }

    // Run the replay
    const result = await runRrwebHeadless({
      events,
      playbackSpeed: options.speed,
      selectors: options.selectors,
      timeout: options.timeout,
      headless: options.headless
    });

    console.log('Test completed successfully');
    console.log('Results:');
    console.log(JSON.stringify(result, null, 2));

    // Check if all selectors were found
    if (result.elementExists) {
      console.log('✅ All elements were found in the replay');
      process.exit(0);
    } else {
      console.log('❌ Some elements were NOT found in the replay');
      // List which elements were not found
      for (const [selector, exists] of Object.entries(result.selectorResults)) {
        if (!exists) {
          console.log(`  - Element "${selector}" was not found`);
        }
      }
      process.exit(1);
    }
  } catch (error) {
    console.error('Error running test:', error);
    process.exit(1);
  }
}

main();
