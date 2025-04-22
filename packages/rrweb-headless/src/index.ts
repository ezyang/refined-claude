import { chromium, Browser, Page } from 'playwright';
import type { eventWithTime } from 'rrweb/typings/types';
import fs from 'fs/promises';
import path from 'path';

interface RrwebReplayOptions {
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
   * Set to 0 to disable timeout (browser will stay open until manually closed)
   */
  timeout?: number;

  /**
   * Whether to run in headless mode (default: true)
   */
  headless?: boolean;
}

interface RrwebReplayResult {
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
 * Runs a rrweb replay in a browser and checks for element existence
 */
export async function runRrwebReplay(options: RrwebReplayOptions): Promise<RrwebReplayResult> {
  const {
    events,
    playbackSpeed = 1,
    selectors = [],
    timeout = 30000,
    headless = true
  } = options;

  let browser: Browser | null = null;

  try {
    // Launch a browser with the specified headless mode
    console.log(`Launching browser in ${headless ? 'headless' : 'headful'} mode`);
    browser = await chromium.launch({ headless });
    const context = await browser.newContext();
    const page = await context.newPage();

    // Setup page with rrweb player
    await setupRrwebPage(page, events, playbackSpeed, selectors);

    // Wait for the replay to complete
    const totalDuration = calculateReplayDuration(events);
    const waitTime = Math.ceil(totalDuration / playbackSpeed);

    // If timeout is 0, we don't close the browser automatically
    if (timeout === 0) {
      console.log('Browser will remain open (timeout=0). Press Ctrl+C to exit.');

      // Wait indefinitely (until the process is killed)
      // Note: This will keep the process running
      await new Promise(() => {});
    } else {
      // Cap the wait time to the provided timeout
      const effectiveWaitTime = Math.min(waitTime, timeout);
      await page.waitForTimeout(effectiveWaitTime);
    }

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
    // Clean up - only if timeout is not 0
    if (browser && timeout !== 0) {
      await browser.close();
    }
  }
}

/**
 * Sets up the page with rrweb player and injects the events
 */
async function setupRrwebPage(page: Page, events: eventWithTime[], playbackSpeed: number, selectors: string[] = []): Promise<void> {
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
          #status {
            position: fixed;
            bottom: 10px;
            right: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-family: monospace;
          }
          #error {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: #ff5252;
            color: white;
            padding: 10px;
            text-align: center;
            font-family: sans-serif;
            display: none;
          }
          .highlight {
            outline: 2px solid red !important;
            outline-offset: 2px !important;
            background-color: rgba(255, 0, 0, 0.2) !important;
          }
        </style>
      </head>
      <body>
        <div id="replay"></div>
        <div id="status">Loading...</div>
        <div id="error"></div>
        <script>
          // Will be replaced with actual events
          const events = [];
          let replayer;

          // Status tracking
          const statusEl = document.getElementById('status');
          const errorEl = document.getElementById('error');

          // Display error message
          function showError(message) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
            console.error(message);
          }

          // Initialize replayer when page loads
          window.addEventListener('DOMContentLoaded', () => {
            try {
              if (!events || !events.length) {
                showError('No events provided');
                return;
              }

              statusEl.textContent = \`Loaded \${events.length} events\`;

              replayer = new rrweb.Replayer(events, {
                root: document.getElementById('replay'),
                liveMode: false,
                showWarning: false,
                showDebug: false,
                blockClass: 'no-record',
                skipInactive: true
              });

              // Set playback speed
              replayer.setSpeed(${playbackSpeed});
              statusEl.textContent = \`Playing at \${${playbackSpeed}}x speed...\`;

              // Start playback
              replayer.play();

              // Display timing info
              setInterval(() => {
                const currentTime = replayer.getCurrentTime();
                const totalTime = replayer.getMetaData().totalTime;
                const progress = Math.round((currentTime / totalTime) * 100);
                statusEl.textContent = \`Replay: \${progress}% (\${Math.floor(currentTime / 1000)}s / \${Math.floor(totalTime / 1000)}s)\`;
              }, 500);

              // When replay finishes, highlight any selectors that match
              setTimeout(() => {
                const selectors = ${JSON.stringify(selectors || [])};
                if (selectors && selectors.length) {
                  selectors.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => el.classList.add('highlight'));
                    statusEl.textContent = \`Found \${elements.length} matches for \${selector}\`;
                  });
                }
              }, replayer.getMetaData().totalTime / ${playbackSpeed} + 1000);

            } catch (err) {
              showError('Error initializing replayer: ' + err.message);
              console.error(err);
            }
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
  // Check if events array is valid
  if (!events || !Array.isArray(events) || events.length === 0) {
    return 5000; // Default duration if no events
  }

  if (events.length < 2) {
    return 5000; // Default duration if not enough events
  }

  // Ensure the events have timestamp properties
  if (!events[0]?.hasOwnProperty('timestamp') || !events[events.length - 1]?.hasOwnProperty('timestamp')) {
    return 5000; // Default duration if events don't have timestamp
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
  const parsed = JSON.parse(content);
  // Handle both formats: direct array or object with 'events' property
  return Array.isArray(parsed) ? parsed : parsed.events;
}

/**
 * @deprecated Use runRrwebReplay instead
 * Backwards compatibility - this function calls runRrwebReplay with the same parameters
 */
export async function runRrwebHeadless(options: RrwebReplayOptions): Promise<RrwebReplayResult> {
  console.warn('Warning: runRrwebHeadless is deprecated, use runRrwebReplay instead');
  return runRrwebReplay(options);
}

// Export types with backward compatible aliases
export type RrwebHeadlessOptions = RrwebReplayOptions;
export type RrwebHeadlessResult = RrwebReplayResult;
