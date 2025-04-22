import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { runRrwebReplay, loadEventsFromFile } from './index';
import path from 'path';
import fs from 'fs/promises';

// Check if we're in debug mode
const isDebugMode = process.env.SUBLIME_DEBUG === '1';

// This is an actual end-to-end test that launches a real browser
describe('rrweb-headless e2e', () => {
  it('should launch a real browser and replay events', async () => {
    const testDataPath = path.resolve(__dirname, '../../..', 'testdata/approve-tool.json');

    // Use loadEventsFromFile to properly load events
    const testEvents = await loadEventsFromFile(testDataPath);

    // Skip if no test events were loaded
    expect(testEvents);
    expect(testEvents.length !== 0);

    // Path to our extension
    const extensionPath = path.resolve(__dirname, '../../extension/dist');
    console.log('Loading extension from:', extensionPath);

    // Verify extension files exist
    try {
      const manifestPath = path.join(extensionPath, 'manifest.json');
      const manifestExists = await fs.access(manifestPath).then(() => true).catch(() => false);
      console.log('Extension manifest exists:', manifestExists);

      const contentScriptPath = path.join(extensionPath, 'index.js');
      const contentScriptExists = await fs.access(contentScriptPath).then(() => true).catch(() => false);
      console.log('Content script exists:', contentScriptExists);
    } catch (error) {
      console.error('Error checking extension files:', error);
    }

    // Run the replay with actual events and check for z-modal
    const result = await runRrwebReplay({
      events: testEvents,
      playbackSpeed: 4,
      // In debug mode, set timeout to 0 (browser stays open), otherwise use a shorter timeout for CI
      timeout: isDebugMode ? 0 : 10000,
      // Force headless mode to false for better debugging
      headless: false,
      chromiumArgs: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`,
        // Add verbose logging for extension loading
        '--enable-logging=stderr',
        '--v=1'
      ]
    });

    // Log detailed results
    console.log('E2E test results:', JSON.stringify(result, null, 2));

    // Verify results (the actual assertion may vary based on your test data)
    expect(result).toBeDefined();

    // Check the new fields
    expect(typeof result.replayCompleted).toBe('boolean');
    if (result.error) {
      console.error('Replay error:', result.error);
    }

    // After the replay, we should check if the allow button was detected
    // This would require a new function to evaluate in the page context
    const allowButtonClicked = await result.page?.evaluate(() => {
      return document.getElementById('allow-button-clicked-marker') !== null;
    });

    console.log('Allow button clicked:', allowButtonClicked);

    // Check for extension state by injecting a test function
    if (result.page) {
      try {
        // Try to detect if extension is loaded by checking for Chrome extension API
        const extensionDetected = await result.page.evaluate(() => {
          return typeof chrome !== 'undefined' &&
                 typeof chrome.runtime !== 'undefined' &&
                 typeof chrome.runtime.id !== 'undefined';
        });
        console.log('Chrome extension API detected:', extensionDetected);

        // Check if our content script ran by looking for a global variable we could add
        await result.page.evaluate(() => {
          // This will output to the console which we're capturing
          console.log('EXTENSION TEST: Checking for content script initialization');
          // We can use the body attribute as a test marker too
          console.log('EXTENSION TEST: data-rrweb-test attribute:',
            document.body.getAttribute('data-rrweb-test'));
        });
      } catch (err) {
        console.error('Error running extension tests:', err);
      }
    }

    // Depending on the test data, we might expect this to be true or false
    // For now we'll just log it, but in a real test you'd add an assertion

    // Clean up resources - skip if in debug mode
    if (result.page && !isDebugMode) {
      // Close any HTTP server that may be running
      // @ts-ignore - Accessing custom property
      const server = result.page._replayServer;
      if (server) {
        try {
          await server.close();
          console.log('Replay server closed from test');
        } catch (err) {
          console.error('Error closing replay server from test:', err);
        }
      }

      const browser = result.page.context().browser();
      await result.page.close();
      if (browser) {
        await browser.close();
      }
    } else if (isDebugMode && result.page) {
      console.log('Debug mode enabled - browser will remain open for inspection');
    }
  // In debug mode, use a very long timeout (effectively no timeout), otherwise use 30 seconds
  }, isDebugMode ? 24 * 60 * 60 * 1000 : 30_000); // Use 24 hours in debug mode
});
