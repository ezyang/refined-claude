import { chromium, Browser, Page } from 'playwright';
import type { eventWithTime } from 'rrweb/typings/types';
import fs from 'fs/promises';
import path from 'path';

interface RrwebHeadlessOptions {
  /**
   * The rrweb events to replay
   */
  events: eventWithTime[];

  /**
   * Playback speed multiplier (default: 1)
   */
  playbackSpeed?: number;

  /**
   * CSS selectors to check for existence after replay
   */
  selectors?: string[];

  /**
   * Timeout in milliseconds (default: 30000)
   */
  timeout?: number;
}

interface RrwebHeadlessResult {
  /**
   * Whether all specified elements exist
   */
  elementExists: boolean;

  /**
   * Detailed results for each selector
   */
  selectorResults: Record<string, boolean>;
}

/**
 * Runs a rrweb replay in a headless browser and checks for element existence
 */
export async function runRrwebHeadless(options: RrwebHeadlessOptions): Promise<RrwebHeadlessResult> {
  const {
    events,
    playbackSpeed = 1,
    selectors = [],
    timeout = 30000
  } = options;

  let browser: Browser | null = null;

  try {
    // Launch a browser
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();

    // Setup page with rrweb player
    await setupRrwebPage(page, events, playbackSpeed);

    // Wait for the replay to complete
    const totalDuration = calculateReplayDuration(events);
    const waitTime = Math.ceil(totalDuration / playbackSpeed);

    // Cap the wait time to the provided timeout
    const effectiveWaitTime = Math.min(waitTime, timeout);
    await page.waitForTimeout(effectiveWaitTime);

    // Check for the existence of the specified selectors
    const selectorResults: Record<string, boolean> = {};

    for (const selector of selectors) {
      const exists = await page.evaluate((sel) => {
        return document.querySelector(sel) !== null;
      }, selector);

      selectorResults[selector] = exists;
    }

    const elementExists = Object.values(selectorResults).every(Boolean);

    return {
      elementExists,
      selectorResults
    };
  } finally {
    // Clean up
    if (browser) {
      await browser.close();
    }
  }
}

/**
 * Sets up the page with rrweb player and injects the events
 */
async function setupRrwebPage(page: Page, events: eventWithTime[], playbackSpeed: number): Promise<void> {
  // Create HTML content with rrweb scripts
  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>rrweb Replay</title>
        <script src="https://cdn.jsdelivr.net/npm/rrweb@latest/dist/rrweb.min.js"></script>
        <style>
          body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }
          #replay { width: 100%; height: 100%; }
        </style>
      </head>
      <body>
        <div id="replay"></div>
        <script>
          // Will be replaced with actual events
          const events = [];

          // Initialize replayer when page loads
          window.addEventListener('DOMContentLoaded', () => {
            const replayer = new rrweb.Replayer(events, {
              root: document.getElementById('replay'),
              liveMode: false,
              showWarning: false,
              showDebug: false,
              blockClass: 'no-record',
              skipInactive: true
            });

            // Set playback speed
            replayer.setSpeed(${playbackSpeed});

            // Start playback
            replayer.play();
          });
        </script>
      </body>
    </html>
  `;

  // Replace the events placeholder with actual events
  const htmlWithEvents = html.replace(
    'const events = [];',
    `const events = ${JSON.stringify(events)};`
  );

  // Navigate to the HTML content
  await page.setContent(htmlWithEvents);
}

/**
 * Calculate the total duration of the replay in milliseconds
 */
function calculateReplayDuration(events: eventWithTime[]): number {
  if (events.length < 2) {
    return 5000; // Default duration if not enough events
  }

  const firstEventTime = events[0].timestamp;
  const lastEventTime = events[events.length - 1].timestamp;

  return lastEventTime - firstEventTime + 1000; // Add 1 second buffer
}

/**
 * Load rrweb events from a JSON file
 */
export async function loadEventsFromFile(filePath: string): Promise<eventWithTime[]> {
  const content = await fs.readFile(filePath, 'utf-8');
  return JSON.parse(content);
}

/**
 * Utility function to run a replay on the test data file
 */
export async function runTestData(testDataPath: string = '../../testdata/approve-tool.json'): Promise<RrwebHeadlessResult> {
  const resolvedPath = path.resolve(__dirname, testDataPath);
  const events = await loadEventsFromFile(resolvedPath);

  return runRrwebHeadless({
    events,
    playbackSpeed: 4,
    selectors: ['.z-modal']
  });
}
