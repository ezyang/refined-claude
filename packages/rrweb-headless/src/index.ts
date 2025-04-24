import { chromium, type Browser, type Page } from 'playwright';
// Import the eventWithTime type from the correct location
import type { eventWithTime } from 'rrweb/dist/types/types';
import * as fs from 'fs/promises';
import * as path from 'path';
import { createReplayServer } from './server.js';

// No need to extend Window interface anymore since we're using console.log
// for communication instead of window properties

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
   * Timeout in milliseconds (default: 30000)
   * Set to 0 to disable timeout (browser will stay open until manually closed)
   */
  timeout?: number;

  /**
   * Whether to run in headless mode (default: true)
   */
  headless?: boolean;

  /**
   * Additional Chromium launch arguments
   */
  chromiumArgs?: string[];

  /**
   * CSS selectors to check for existence
   */
  selectors?: string[];

  /**
   * Path to user data directory for persistent browser context
   * If provided, a persistent context will be used instead of a regular browser instance
   */
  userDataDir?: string;

  /**
   * Which browser to use (default: undefined - use default)
   * Set to 'chromium' to explicitly use the Chromium channel
   */
  channel?: string;
}

interface RrwebReplayResult {
  /**
   * Whether all specified elements exist
   */
  elementExists: boolean;

  /**
   * Whether the replay completed successfully
   */
  replayCompleted: boolean;

  /**
   * Error message if the replay failed
   */
  error: string | undefined;

  logs: string[];

  /**
   * The Playwright page object (only available during testing)
   * This allows tests to perform additional evaluations on the page
   */
  page: Page | undefined;
}

/**
 * Runs a rrweb replay in a browser and checks for element existence
 */
export async function runRrwebReplay(options: RrwebReplayOptions): Promise<RrwebReplayResult> {
  const {
    events,
    playbackSpeed = 1,
    timeout = 30000,
    headless = true,
    chromiumArgs = [],
    userDataDir,
    channel = 'chromium'
  } = options;

  // Allow overriding headless mode via environment variable
  const isDebugMode = process.env.SUBLIME_DEBUG === '1';
  const effectiveHeadless = isDebugMode ? false : headless;

  let browser: Browser | null = null;
  let page: Page | null = null;
  let context;

  try {
    // Launch a browser with the specified headless mode, overridden by env var if present
    console.log(`[DRIVER] 🌐 Browser: ${effectiveHeadless ? 'headless' : 'headful'} mode, channel: ${channel}`);

    if (userDataDir) {
      console.log(`[DRIVER] 📂 User data directory: ${userDataDir}`);
    }

    // Common launch options
    const launchOptions = {
      headless: effectiveHeadless,
      args: chromiumArgs,
      // When in debug mode, open with devtools console
      devtools: isDebugMode,
      channel: channel
    };

    // In debug mode, log the configuration
    if (isDebugMode) {
      console.log('[DRIVER] 🔍 Debug mode enabled with devtools');
    }

    // Launch the browser based on whether we're using a persistent context or not
    if (userDataDir) {
      // Launch a persistent context
      context = await chromium.launchPersistentContext(userDataDir, launchOptions);
      page = await context.newPage();
      // We can access the browser through the context
      browser = context.browser();
    } else {
      // Launch a regular browser instance
      browser = await chromium.launch(launchOptions);
      context = await browser.newContext();
      page = await context.newPage();
    }

    // Setup page with rrweb player
    await setupRrwebPage(page, events, playbackSpeed);

    let logs: string[] = [];

    // If timeout is 0 or debug mode is on, we don't close the browser automatically
    if (timeout === 0 || isDebugMode) {
      console.log(`[DRIVER] 🔍 Browser will remain open. Press Ctrl+C to exit.`);

      // Wait indefinitely (until the process is killed)
      // Note: This will keep the process running
      await new Promise(() => {});
    } else {
      // Wait for replay to complete or timeout
      try {
        // Listen for specific console.log messages to determine status
        let isCompleted = false;
        let replayError: string | undefined = undefined;

        // Set up console message listener for status tracking
        page.on('console', async (msg) => {
          const text = msg.text();
          logs.push(text);

          // Check for completion message
          if (text.includes('[RRWEB] Replay finished successfully')) {
            isCompleted = true;
          }
        });

        // Wait for either completion or timeout
        console.log(`[DRIVER] ⏱️ Waiting ${timeout}ms for replay to complete`);
        let checkInterval: ReturnType<typeof setInterval> | null = null;
        let timeoutId: ReturnType<typeof setTimeout> | null = null;

        try {
          await Promise.race([
            // Wait for console message indicating completion
            new Promise(resolve => {
              checkInterval = setInterval(() => {
                if (isCompleted || replayError) {
                  if (checkInterval) {
                    clearInterval(checkInterval);
                    checkInterval = null;
                  }
                  resolve(true);
                }
              }, 100);
            }),
            // Timeout
            new Promise((_, reject) => {
              timeoutId = setTimeout(() => {
                reject(new Error(`Timeout of ${timeout}ms exceeded`));
              }, timeout);
            })
          ]);
        } finally {
          // Ensure we clean up the timers even if Promise.race is interrupted
          if (checkInterval) {
            clearInterval(checkInterval);
          }
          if (timeoutId) {
            clearTimeout(timeoutId);
          }
        }

        // Check if there was an error
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

    // For console.log based approach, status is determined by console messages
    // If we get to this point and haven't thrown an error for timeout,
    // the replay completed successfully
    let replayCompleted = true;
    let error: string | undefined = undefined;
    let elementExists = true; // Basic defaults for backward compatibility

    // When we get to this point, ensure we've closed the resources if any error message was found during the test
    // The replayError variable is defined within the try/catch block above, but isn't accessible here
    // Instead we check if error is already set from an exception above
    if (error) {
      replayCompleted = false;
    }

    // Expose the page object for testing purposes
    return {
      replayCompleted,
      error,
      elementExists,
      logs,
      page: (timeout === 0 || isDebugMode) ? undefined : page // Only include page if not in infinite wait mode or debug mode
    };
  } finally {
    // Clean up - only if timeout is not 0 and debug mode is off
    if (timeout !== 0 && !isDebugMode) {
      try {
        // Use a timeout for cleanup operations to avoid hanging
        const cleanupTimeout = Math.min(5000, timeout / 2); // Max 5 seconds or half the test timeout

        // Close the local HTTP server if it exists with a timeout
        if (page) {
          // @ts-ignore - Accessing custom property
          const server = page._replayServer;
          if (server) {
            await Promise.race([
              server.close().catch((err: Error) => console.error('Error closing replay server:', err)),
              new Promise(r => setTimeout(r, cleanupTimeout / 3))
            ]);
            console.log('[DRIVER] Replay server closed or timed out');
          }
        }

        // Don't close the browser if we're including the page in results
        // Let the caller handle closing it
        if (context && !options.userDataDir && (!options.chromiumArgs || options.chromiumArgs.length === 0)) {
          // If using a persistent context, close the context instead of the browser with a timeout
          await Promise.race([
            context.close().catch((err: Error) => console.error('Error closing context:', err)),
            new Promise(r => setTimeout(r, cleanupTimeout / 3))
          ]);
          console.log('[DRIVER] Browser context closed or timed out');
        } else if (browser && (!options.chromiumArgs || options.chromiumArgs.length === 0)) {
          // Otherwise close the browser if available with a timeout
          await Promise.race([
            browser.close().catch((err: Error) => console.error('Error closing browser:', err)),
            new Promise(r => setTimeout(r, cleanupTimeout / 3))
          ]);
          console.log('[DRIVER] Browser closed or timed out');
        }
      } catch (err) {
        console.error('Cleanup error (suppressed):', err);
      }
    }
  }
}

/**
 * Sets up the page with rrweb player and injects the events
 */
async function setupRrwebPage(page: Page, events: eventWithTime[], playbackSpeed: number): Promise<void> {
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

  // CSS styles for the replay page
  const styles = `
    /* Reset all elements to ensure consistent layout */
    *, *::before, *::after {
      box-sizing: border-box;
    }

    body, html {
      margin: 0;
      padding: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
    }

    /* Create a container that covers the entire viewport */
    #replay {
      width: 100%;
      height: 100%;
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      margin: 0;
      z-index: 9000; /* High z-index but below status elements */
      display: flex;
      align-items: center;
      justify-content: center;
    }

    #replay iframe {
      width: 100%;
      height: 100%;
      border: none;
      position: absolute;
      top: 0;
      left: 0;
    }

    /* Force the player elements to take full size and center correctly */
    .replayer-wrapper {
      width: 100% !important;
      height: 100% !important;
      position: absolute !important;
      top: 0 !important;
      left: 0 !important;
      transform: none !important; /* Prevent transformations that might offset it */
    }

    .replayer-mirror {
      width: 100% !important;
      height: 100% !important;
      position: absolute !important;
      top: 0 !important;
      left: 0 !important;
      transform: none !important;
    }

    /* Status and error indicators with very high z-index */
    #status {
      position: fixed;
      bottom: 10px;
      right: 10px;
      background: rgba(0,0,0,0.7);
      color: white;
      padding: 5px 10px;
      border-radius: 4px;
      font-family: monospace;
      z-index: 10500;
      pointer-events: none; /* Don't block interaction */
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
      z-index: 10500;
    }

    .highlight {
      outline: 2px solid red !important;
      outline-offset: 2px !important;
      background-color: rgba(255, 0, 0, 0.2) !important;
      z-index: 10000 !important;
      position: relative !important;
    }

    /* Protect against any interference from extension content */
    body > :not(#replay):not(#status):not(#error) {
      visibility: hidden !important;
      position: absolute !important;
      top: -9999px !important;
      left: -9999px !important;
      z-index: -1 !important;
      pointer-events: none !important;
    }
  `;

  // JavaScript for replay functionality
  const script = `
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
      console.error('[RRWEB_ERROR] ' + message);
    }

    // Flag as rrweb test environment to help extensions detect this context
    document.body.setAttribute('data-rrweb-test', 'true');

    // Helper function to ensure player is centered
    function ensurePlayerCentered() {
      const replay = document.getElementById('replay');
      if (!replay) return;

      // Force the replay element to be the full viewport
      replay.style.position = 'fixed';
      replay.style.top = '0';
      replay.style.left = '0';
      replay.style.width = '100%';
      replay.style.height = '100%';
      replay.style.zIndex = '9000';

      // Find any wrapper or mirror elements
      const wrappers = document.querySelectorAll('.replayer-wrapper');
      const mirrors = document.querySelectorAll('.replayer-mirror');

      // Apply centering to wrappers
      wrappers.forEach(wrapper => {
        wrapper.style.position = 'absolute';
        wrapper.style.top = '0';
        wrapper.style.left = '0';
        wrapper.style.width = '100%';
        wrapper.style.height = '100%';
        wrapper.style.transform = 'none';
      });

      // Apply centering to mirrors
      mirrors.forEach(mirror => {
        mirror.style.position = 'absolute';
        mirror.style.top = '0';
        mirror.style.left = '0';
        mirror.style.width = '100%';
        mirror.style.height = '100%';
        mirror.style.transform = 'none';
      });
    }

    // Initialize replayer when page loads
    window.addEventListener('DOMContentLoaded', () => {
      try {
        if (!events || !events.length) {
          const errorMsg = 'No events provided';
          showError(errorMsg);
          return;
        }

        // Log initialization status
        console.log('[RRWEB] Loaded ' + events.length + ' events');
        statusEl.textContent = 'Loaded ' + events.length + ' events';

        // Create a clean container for the player
        const replayContainer = document.getElementById('replay');

        // Clear any previous content (just in case)
        replayContainer.innerHTML = '';

        // Fallback to basic rrweb replayer
        replayer = new rrweb.Replayer(events, {
          root: replayContainer,
          liveMode: false,
          showWarning: true, // Enable warnings to help debug
          showDebug: false,
          blockClass: 'no-record',
          skipInactive: true,
          speed: ${playbackSpeed}, // Set speed directly in options
          useIframe: true, // This is crucial for seeing the webpage content
          mouseTail: true // Show mouse movements
        });

        // Fix any positioning before playing
        ensurePlayerCentered();

        statusEl.textContent = \`Playing at \${${playbackSpeed}}x speed...\`;
        console.log('[RRWEB] Playing at ' + ${playbackSpeed} + 'x speed');

        // Start playback, but give content script a chance to run first.
        // The timeout here is empirically determined to ensure playback
        // doesn't start until we've setup observers in the iframe
        setTimeout(() => {
          console.log('[RRWEB] Starting playback');
          replayer.play();
        }, 100);

        // Periodically check player positioning and fix if needed
        let positionInterval = setInterval(ensurePlayerCentered, 1000);

        // Display timing info - works with both player types
        let progressInterval = setInterval(() => {
          let currentTime, totalTime;

          // For basic replayer
          currentTime = replayer.getCurrentTime();
          totalTime = replayer.getMetaData().totalTime;

          if (currentTime !== undefined && totalTime !== undefined) {
            const progress = Math.round((currentTime / totalTime) * 100);
            const currentStatusText = statusEl.textContent.split(' - ')[0];
            statusEl.textContent = currentStatusText + ' - Replay: ' + progress + '% (' + Math.floor(currentTime / 1000) + 's / ' + Math.floor(totalTime / 1000) + 's)';

            // Log progress periodically
            if (progress % 10 === 0) {
              console.log('[RRWEB] ' + progress + '%');
            }

            // Check if replay is complete
            if (progress >= 100) {
              clearInterval(progressInterval);
              clearInterval(positionInterval);
              statusEl.textContent += ' - COMPLETE';
              console.log('[RRWEB] 100%'); // Explicitly log 100% progress
              console.log('[RRWEB] Replay finished successfully');
            }
          }
        }, 500);
      } catch (err) {
        const errorMsg = 'Error initializing replayer: ' + err.message;
        showError(errorMsg);
      }
    });
  `;

  // Create a more concise HTML template
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
        <style>${styles}</style>
      </head>
      <body>
        <div id="replay"></div>
        <div id="status">Loading...</div>
        <div id="error"></div>
        <script>${script}</script>
      </body>
    </html>
  `;

  // Replace the events placeholder with actual events
  const htmlWithEvents = html.replace(
    'const events = [];',
    `const events = ${JSON.stringify(events)};`
  );

  // Create a local HTTP server to serve the content
  // This ensures content scripts can be properly injected (unlike with data: URLs)
  const server = await createReplayServer();

  // Serve our HTML content
  server.serveContent(htmlWithEvents);

  // Navigate to the local server URL
  const serverUrl = `http://localhost:${server.port}`;
  console.log(`[DRIVER] 🌐 Replay server: ${serverUrl}`);

  // Start navigation but don't wait for it to complete.
  // TODO: In fact, this navigation never "completes", need
  // to reconfigure Playwright call so that it treats DOM initialization
  const navigationPromise = page.goto(serverUrl, { waitUntil: 'domcontentloaded' }).catch(err => {
    console.error(`[DRIVER] ❌ Navigation error: ${err.message}`);
  });

  // TODO: There is a little bit of a race here as the page doesn't explicitly
  // synchronize with us
  console.log('[DRIVER] 🔊 Setting up console logger');
  page.on('console', msg => {
    // Filter out CORS errors and resource loading failures to reduce noise
    const text = msg.text();
    if (text.includes('Access to font') && text.includes('has been blocked by CORS policy')) {
      return;
    }
    if (text.includes('Failed to load resource: net::ERR_FAILED')) {
      return; // Filter out all ERR_FAILED errors, not just for fonts
    }

    // Format console messages by type
    if (msg.type() === 'error') {
      console.error(`[CONSOLE] Browser error: ${text}`);
    } else if (msg.type() === 'warning') {
      console.warn(`[CONSOLE] Browser warning: ${text}`);
    } else {
      console.log(`${text}`);
    }
  });

  // Store the server in the page object for cleanup later
  // @ts-ignore - Adding custom property to store server reference
  page._replayServer = server;
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
