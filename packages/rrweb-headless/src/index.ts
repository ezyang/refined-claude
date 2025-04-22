import { chromium, Browser, Page } from 'playwright';
import type { eventWithTime } from 'rrweb/typings/types';
import fs from 'fs/promises';
import path from 'path';

// Extend Window interface to include our custom properties
declare global {
  interface Window {
    __REPLAY_FINISHED?: boolean;
    __REPLAY_ERROR?: string;
  }
}

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

  /**
   * Whether the replay completed successfully
   */
  replayCompleted: boolean;

  /**
   * Error message if the replay failed
   */
  error?: string;
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

    // If timeout is 0, we don't close the browser automatically
    if (timeout === 0) {
      console.log('Browser will remain open (timeout=0). Press Ctrl+C to exit.');

      // Wait indefinitely (until the process is killed)
      // Note: This will keep the process running
      await new Promise(() => {});
    } else {
      // Wait for replay to complete or timeout
      try {
        // Wait for the replay finished flag to be set with a maximum timeout
        await Promise.race([
          page.waitForFunction(() => window.__REPLAY_FINISHED === true, { timeout }),
          page.waitForFunction(() => window.__REPLAY_ERROR !== undefined, { timeout })
        ]);

        // Check if there was an error
        const replayError = await page.evaluate(() => window.__REPLAY_ERROR);
        if (replayError) {
          throw new Error(`Replay error: ${replayError}`);
        }
      } catch (err) {
        // If the timeout was reached without the flag being set
        if ((err as Error).message.includes('Timeout')) {
          console.warn(`Replay did not complete within the specified timeout (${timeout}ms)`);
        } else {
          throw err;
        }
      }
    }

    // Check if the replay completed or errored out
    let replayCompleted = false;
    let error: string | undefined = undefined;

    try {
      replayCompleted = await page.evaluate(() => window.__REPLAY_FINISHED === true);
      error = await page.evaluate(() => window.__REPLAY_ERROR);
    } catch (evalError) {
      console.error('Error evaluating replay status:', evalError);
    }

    // Check for the existence of the specified selectors
    const selectorResults: Record<string, boolean> = {};

    for (const selector of selectors) {
      const exists = await page.evaluate((sel) => {
        // Look for the iframe that rrweb-replay creates
        const iframe = document.querySelector('#replay iframe');

        // If iframe exists, search within its document
        if (iframe && iframe.contentDocument) {
          return iframe.contentDocument.querySelector(sel) !== null;
        }

        // Fallback to the main document if iframe not found
        return document.querySelector(sel) !== null;
      }, selector);

      selectorResults[selector] = exists;
    }

    const elementExists = Object.values(selectorResults).every(Boolean);

    return {
      elementExists,
      selectorResults,
      replayCompleted,
      error
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
  // Import rrweb and rrweb-player from node_modules
  const rrwebPath = require.resolve('rrweb/dist/rrweb.min.js');
  const rrwebContent = await fs.readFile(rrwebPath, 'utf-8');

  // Try to find and import rrweb-player
  let rrwebPlayerContent = '';
  let rrwebPlayerCssContent = '';
  try {
    const rrwebPlayerPath = require.resolve('rrweb-player/dist/index.js');
    rrwebPlayerContent = await fs.readFile(rrwebPlayerPath, 'utf-8');

    // Also try to load the CSS for rrweb-player
    try {
      const rrwebPlayerCssPath = require.resolve('rrweb-player/dist/style.css');
      rrwebPlayerCssContent = await fs.readFile(rrwebPlayerCssPath, 'utf-8');
    } catch (cssError) {
      console.warn('rrweb-player CSS not found, player may not display correctly');
    }
  } catch (e) {
    console.warn('rrweb-player not found, using basic replayer');
  }

  // Create HTML content with rrweb scripts
  const html = `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>rrweb Replay</title>
        <script>${rrwebContent}</script>
        ${rrwebPlayerContent ? `<script>${rrwebPlayerContent}</script>` : ''}
        ${rrwebPlayerCssContent ? `<style>${rrwebPlayerCssContent}</style>` : ''}
        <style>
          body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }
          #replay {
            width: 100%;
            height: 100%;
            position: relative;
          }
          /* Ensure iframes are visible and sized properly */
          #replay iframe {
            width: 100%;
            height: 100%;
            border: none;
            position: absolute;
            top: 0;
            left: 0;
          }
          /* Make sure the replayer UI components don't obscure content */
          .replayer-wrapper {
            width: 100% !important;
            height: 100% !important;
          }
          /* For the mirror element that shows the content */
          .replayer-mirror {
            width: 100% !important;
            height: 100% !important;
          }
          #status {
            position: fixed;
            bottom: 10px;
            right: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-family: monospace;
            z-index: 10000;
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
            z-index: 10000;
          }
          .highlight {
            outline: 2px solid red !important;
            outline-offset: 2px !important;
            background-color: rgba(255, 0, 0, 0.2) !important;
            z-index: 10000 !important;
            position: relative !important;
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

          // Initialize global flags for replay status
          window.__REPLAY_FINISHED = false;
          window.__REPLAY_ERROR = undefined;

          // Initialize replayer when page loads
          window.addEventListener('DOMContentLoaded', () => {
            try {
              if (!events || !events.length) {
                const errorMsg = 'No events provided';
                showError(errorMsg);
                window.__REPLAY_ERROR = errorMsg;
                return;
              }

              // Check if events contain full snapshot
              const hasFullSnapshot = events.some(event =>
                event.type === 2 && // Full snapshot type
                event.data &&
                event.data.node
              );

              if (!hasFullSnapshot) {
                console.warn('Warning: Events do not contain a full snapshot, webpage content may not render properly');
              }

              statusEl.textContent = 'Loaded ' + events.length + ' events' + (hasFullSnapshot ? ' (snapshot found)' : ' (no snapshot found)');

              // Check if rrwebPlayer is available
              if (typeof rrwebPlayer !== 'undefined') {
                // Use rrweb-player
                replayer = new rrwebPlayer({
                  target: document.getElementById('replay'),
                  props: {
                    events,
                    showController: true, // Show controller to help with debugging
                    skipInactive: true,
                    width: window.innerWidth,
                    height: window.innerHeight,
                    // Make sure to enable iframe rendering
                    useIframe: true // This is crucial for seeing the webpage content
                  }
                });

                // Set playback speed
                replayer.setSpeed(${playbackSpeed});
                statusEl.textContent = \`Playing at \${${playbackSpeed}}x speed...\`;

                // Start playback
                replayer.play();
              } else {
                // Fallback to basic rrweb replayer
                replayer = new rrweb.Replayer(events, {
                  root: document.getElementById('replay'),
                  liveMode: false,
                  showWarning: true, // Enable warnings to help debug
                  showDebug: false,
                  blockClass: 'no-record',
                  skipInactive: true,
                  speed: ${playbackSpeed}, // Set speed directly in options
                  // Make sure to enable iframe rendering
                  useIframe: true, // This is crucial for seeing the webpage content
                  mouseTail: true // Show mouse movements
                });

                statusEl.textContent = \`Playing at \${${playbackSpeed}}x speed...\`;

                // Start playback
                replayer.play();
              }

              // Monitor for DOM changes to detect if content is rendered
              let contentCheckInterval;
              let contentRendered = false;

              contentCheckInterval = setInterval(() => {
                // Check for any content in the replay container
                const replayContainer = document.getElementById('replay');

                // Look for either iframe or mirror content
                const hasIframe = replayContainer.querySelector('iframe');
                const hasMirror = replayContainer.querySelector('.replayer-mirror');

                if (hasIframe || hasMirror) {
                  const contentInIframe = hasIframe &&
                    (hasIframe.contentDocument &&
                     hasIframe.contentDocument.body &&
                     hasIframe.contentDocument.body.childElementCount > 0);

                  const contentInMirror = hasMirror && hasMirror.childElementCount > 0;

                  if (contentInIframe || contentInMirror) {
                    contentRendered = true;
                    console.log('Content successfully rendered');
                    statusEl.style.backgroundColor = 'rgba(0,128,0,0.7)';
                    clearInterval(contentCheckInterval);
                  }
                }

                // If no content after 5 seconds, show warning
                if (!contentRendered && window.performance.now() > 5000) {
                  const warningMsg = 'No content detected in replayer. Check if events contain full snapshot.';
                  console.warn(warningMsg);
                  statusEl.style.backgroundColor = 'rgba(255,127,0,0.7)';

                  // If still no content after 10 seconds, consider it an error
                  if (window.performance.now() > 10000 && !contentRendered) {
                    window.__REPLAY_ERROR = 'Failed to render content: ' + warningMsg;
                    clearInterval(contentCheckInterval);
                  }
                }
              }, 1000);

              // Display timing info - works with both player types
              let progressInterval = setInterval(() => {
                let currentTime, totalTime;

                if (typeof rrwebPlayer !== 'undefined' && replayer) {
                  // For rrweb-player we need to get time differently
                  // Use first/last event timestamps as an approximation
                  const firstTimestamp = events[0].timestamp;
                  const lastTimestamp = events[events.length - 1].timestamp;
                  totalTime = lastTimestamp - firstTimestamp;

                  // Here we're approximating current time based on when replay started
                  const replayStartTime = window.performance.now() - (window.performance.now() % 500);
                  const elapsedTime = (window.performance.now() - replayStartTime) * ${playbackSpeed};
                  currentTime = Math.min(elapsedTime, totalTime);
                } else if (replayer) {
                  // For basic replayer
                  currentTime = replayer.getCurrentTime();
                  totalTime = replayer.getMetaData().totalTime;
                }

                if (currentTime !== undefined && totalTime !== undefined) {
                  const progress = Math.round((currentTime / totalTime) * 100);
                  const currentStatusText = statusEl.textContent.split(' - ')[0];
                  statusEl.textContent = currentStatusText + ' - Replay: ' + progress + '% (' + Math.floor(currentTime / 1000) + 's / ' + Math.floor(totalTime / 1000) + 's)';

                  // Check if replay is complete
                  if (progress >= 100) {
                    window.__REPLAY_FINISHED = true;
                    clearInterval(progressInterval);
                    statusEl.textContent += ' - COMPLETE';
                    console.log('Replay completed');
                  }
                }
              }, 500);

              // When replay finishes, highlight any selectors that match
              const replayDuration = events[events.length - 1].timestamp - events[0].timestamp;
              setTimeout(() => {
                const selectors = ${JSON.stringify(selectors || [])};
                if (selectors && selectors.length) {
                  selectors.forEach(selector => {
                    // Look for the iframe that rrweb-replay creates
                    const iframe = document.querySelector('#replay iframe');
                    let elements = [];

                    // If iframe exists, search within its document
                    if (iframe && iframe.contentDocument) {
                      elements = iframe.contentDocument.querySelectorAll(selector);
                      // Add highlight class to elements inside iframe
                      elements.forEach(el => el.classList.add('highlight'));
                    } else {
                      // Fallback to the main document if iframe not found
                      elements = document.querySelectorAll(selector);
                      elements.forEach(el => el.classList.add('highlight'));
                    }

                    statusEl.textContent = \`Found \${elements.length} matches for \${selector}\`;
                  });
                }

                // Mark replay as finished if not already marked
                window.__REPLAY_FINISHED = true;
              }, replayDuration / ${playbackSpeed} + 1000);

            } catch (err) {
              const errorMsg = 'Error initializing replayer: ' + err.message;
              showError(errorMsg);
              console.error(err);
              window.__REPLAY_ERROR = errorMsg;
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
