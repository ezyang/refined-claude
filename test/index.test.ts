import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { runRrwebReplay, loadEventsFromFile } from '@refined-claude/rrweb-headless';
import path from 'path';
import fs from 'fs/promises';

// Check if we're in debug mode
const isDebugMode = process.env.SUBLIME_DEBUG === '1';

/**
 * Run a test for a specific rrweb replay file
 */
async function runReplayTest(
  testFile: string,
  validateResults: (result: any) => void,
  speed?: number
): Promise<void> {
  const testDataPath = path.resolve(__dirname, '..', `testdata/${testFile}`);

  // Use loadEventsFromFile to properly load events
  const testEvents = await loadEventsFromFile(testDataPath);

  // Skip if no test events were loaded
  expect(testEvents).not.toBeUndefined();
  expect(testEvents.length).not.toBe(0);

  // 🔄 Test setup
  console.log('🔄 TEST MILESTONE: Setup started');

  // Path to our extension
  const extensionPath = path.resolve(__dirname, '../dist');

  // Verify extension files exist
  try {
    const manifestPath = path.join(extensionPath, 'manifest.json');
    const contentScriptPath = path.join(extensionPath, 'index.js');

    const manifestExists = await fs
      .access(manifestPath)
      .then(() => true)
      .catch(() => false);
    const contentScriptExists = await fs
      .access(contentScriptPath)
      .then(() => true)
      .catch(() => false);

    if (!manifestExists || !contentScriptExists) {
      console.warn(
        '⚠️ Extension files check:',
        manifestExists ? '✓ manifest.json' : '✗ manifest.json missing',
        contentScriptExists ? '✓ index.js' : '✗ index.js missing'
      );
    }
  } catch (error) {
    console.error('❌ Error checking extension files:', error);
  }

  // Create a unique temporary user data directory for this test run
  const userDataDir = path.resolve(
    __dirname,
    '../../../.tmp-playwright',
    `test-run-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
  );
  try {
    await fs.mkdir(userDataDir, { recursive: true });
    console.log(`🔄 Created fresh profile at: ${userDataDir}`);
  } catch (error) {
    console.error('❌ Error creating user data directory:', error);
  }

  // Configure test timeout
  const testTimeout = isDebugMode ? 0 : 25000; // 25 seconds (less than test timeout of 30s)
  console.log('🔄 TEST MILESTONE: Setup completed');

  const result = await runRrwebReplay({
    events: testEvents,
    playbackSpeed: speed ?? 8, // Use provided speed or default to 8192
    // In debug mode, set timeout to 0 (browser stays open), otherwise use a timeout that's shorter than the test timeout
    timeout: testTimeout,
    // Use persistent profile
    userDataDir: userDataDir,
    // Explicitly specify the chromium channel
    channel: 'chromium',
    chromiumArgs: [
      `--disable-extensions-except=${extensionPath}`,
      `--load-extension=${extensionPath}`,
      // Add verbose logging for extension loading
      '--enable-logging=stderr',
      '--v=1',
    ],
  });

  // Log test milestones with consistent formatting
  console.log('🔍 TEST MILESTONE: Result object received');

  // Verify results (the actual assertion may vary based on your test data)
  expect(result).toBeDefined();

  // Check the new fields
  expect(typeof result.replayCompleted).toBe('boolean');
  if (result.error) {
    console.error('❌ TEST ERROR:', result.error);
  }

  // Run test-specific validations
  validateResults(result);

  // Show condensed results
  console.log('📊 TEST RESULTS: Replay completed:', result.replayCompleted);

  // Check for extension state by injecting a test function
  if (result.page) {
    try {
      // Try to detect if extension is loaded by checking for Chrome extension API
      const extensionDetected = await result.page.evaluate(() => {
        return (
          typeof chrome !== 'undefined' &&
          typeof chrome.runtime !== 'undefined' &&
          typeof chrome.runtime.id !== 'undefined'
        );
      });
      console.log('Chrome extension API detected:', extensionDetected);

      // Check if our content script ran by looking for a global variable we could add
      await result.page.evaluate(() => {
        // This will output to the console which we're capturing
        console.log('EXTENSION TEST: Checking for content script initialization');
        // We can use the body attribute as a test marker too
        console.log(
          'EXTENSION TEST: data-rrweb-test attribute:',
          document.body.getAttribute('data-rrweb-test')
        );
      });
    } catch (err) {
      console.error('Error running extension tests:', err);
    }
  }

  // Clean up resources - skip if in debug mode
  if (result.page && !isDebugMode) {
    try {
      console.log('🧹 TEST MILESTONE: Cleanup started');

      // Use a short timeout for cleanup operations to prevent hanging
      const cleanupTimeout = 5000; // 5 seconds max

      // Close any HTTP server that may be running
      // @ts-ignore - Accessing custom property
      const server = result.page._replayServer;
      if (server) {
        try {
          await Promise.race([server.close(), new Promise(r => setTimeout(r, cleanupTimeout / 3))]);
        } catch (err) {
          console.error('❌ Error closing replay server:', err);
        }
      }

      // Get context before closing the page
      const context = result.page.context();

      // Close page and context with timeout
      try {
        await Promise.race([
          result.page.close(),
          new Promise(r => setTimeout(r, cleanupTimeout / 3)),
        ]);
        await Promise.race([context.close(), new Promise(r => setTimeout(r, cleanupTimeout / 3))]);
        console.log('🧹 TEST MILESTONE: Cleanup completed');
      } catch (err) {
        console.error('❌ Error closing browser resources:', err);
      }

      // Clean up the temporary user data directory
      try {
        // Only attempt to remove if not in debug mode
        if (userDataDir.includes('.tmp-playwright')) {
          console.log(`🧹 Removing temporary profile at: ${userDataDir}`);
          await fs.rm(userDataDir, { recursive: true, force: true });
        }
      } catch (err) {
        console.error('❌ Error removing temporary user data directory:', err);
      }
    } catch (err) {
      console.error('❌ Error during cleanup:', err);
    }
  } else if (isDebugMode && result.page) {
    console.log('🔍 Debug mode enabled - browser will remain open for inspection');
  }
}

// This is an actual end-to-end test that launches a real browser
describe.concurrent('rrweb-headless e2e', () => {
  // Test for the approve-tool.json file (Allow button click)
  it(
    'should detect and click the Allow button in approve-tool.json',
    async () => {
      await runReplayTest('approve-tool.json', result => {
        // Check for the Allow button in the logs
        expect(result.logs.some(log => log.includes('Clicking "Allow for this chat" button'))).toBe(
          true
        );
        console.log('✅ Allow button observer test passed!');
      });
    },
    isDebugMode ? 24 * 60 * 60 * 1000 : 60_000
  );

  // Test for the hit-max-length-may-2025.json file (Continue button detection and auto-click)
  it(
    'should detect and click the Continue button in hit-max-length-may-2025.json',
    async () => {
      await runReplayTest('hit-max-length-may-2025.json', result => {
        // Check for the Continue button in the logs
        expect(result.logs.some(log => log.includes('Found Continue button'))).toBe(true);

        // Check that we click it, accepting either the RUNNING → STOPPED transition
        // or the "during page load while in RUNNING state" case
        expect(
          result.logs.some(
            log =>
              log.includes('Clicking "Continue" button after RUNNING -> STOPPED transition') ||
              log.includes('Clicking "Continue" button during page load while in RUNNING state')
          )
        ).toBe(true);

        console.log('✅ Continue button detect and auto-click test passed!');
      });
    },
    isDebugMode ? 24 * 60 * 60 * 1000 : 60_000
  );

  // Test for navigate-to-continue-page.json (should still NOT auto-continue in certain situations)
  it(
    'should not auto-continue in navigate-to-continue-page.json when not in appropriate state',
    async () => {
      await runReplayTest('navigate-to-continue-page.json', result => {
        // Check that we found a Continue button
        expect(result.logs.some(log => log.includes('Found Continue button'))).toBe(true);

        // With our fix, we should still NOT be clicking the button in some conditions
        // Either we see the "during page load" message OR "not in appropriate state" message
        expect(
          result.logs.some(
            log =>
              log.includes('Continue button found during page load, not clicking') ||
              log.includes('Continue button found but not in appropriate state for clicking')
          )
        ).toBe(true);

        // Should NOT see the race condition handling message (if the state isn't RUNNING)
        expect(
          result.logs.some(log =>
            log.includes(
              'Clicking "Continue" button while in RUNNING state (handling race condition)'
            )
          )
        ).toBe(false);

        console.log('✅ No auto-continue when not in appropriate state test passed!');
      });
    },
    isDebugMode ? 24 * 60 * 60 * 1000 : 60_000
  );

  // Test for continue-usage-limit-reached.json (should not attempt to click Continue when usage limit is hit)
  it(
    'should not click Continue button when usage limit is reached',
    async () => {
      await runReplayTest('continue-usage-limit-reached.json', result => {
        // Check that we found at least one Continue button
        expect(result.logs.some(log => log.includes('Found Continue button'))).toBe(true);

        // Check that we properly detected the Continue button but did not attempt to click it
        expect(
          result.logs.some(
            log =>
              log.includes('Continue button found during page load, not clicking') ||
              log.includes('Continue button found but not in appropriate state for clicking')
          )
        ).toBe(true);

        // Verify we never actually tried to click the Continue button
        expect(
          result.logs.some(
            log =>
              log.includes('Clicking "Continue" button after RUNNING -> STOPPED transition') ||
              log.includes('Clicking "Continue" button during page load while in RUNNING state')
          )
        ).toBe(false);

        // Count how many times we detected the Continue button
        const continueButtonDetections = result.logs.filter(log =>
          log.includes('Found Continue button')
        ).length;

        console.log(`Found Continue button ${continueButtonDetections} times but never clicked it`);

        console.log('✅ No Continue button clicks when usage limit reached test passed!');
      });
    },
    isDebugMode ? 24 * 60 * 60 * 1000 : 60_000
  );

  // Test for the simple-response.json file (Response state toggle)
  it(
    'should detect response button state change in simple-response.json',
    async () => {
      await runReplayTest(
        'simple-response.json',
        result => {
          // Check for the response state observer initialization
          expect(
            result.logs.some(log => log.includes('Response state observer setup complete'))
          ).toBe(true);

          // Check for state tracking (using the new log format)
          expect(result.logs.some(log => log.includes('Response state changed:'))).toBe(true);

          // Check for state change detection
          expect(
            result.logs.some(log => log.includes('Response state changed: RUNNING → STOPPED'))
          ).toBe(true);

          console.log('✅ Response state observer test passed!');
        },
        4
      );
    },
    isDebugMode ? 24 * 60 * 60 * 1000 : 60_000
  );
});
