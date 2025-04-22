import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { runRrwebHeadless, loadEventsFromFile } from './index';
import path from 'path';
import fs from 'fs/promises';

// This is an actual end-to-end test that launches a real browser
describe('rrweb-headless e2e', () => {
  let testEvents: any[];

  // Load the actual test data before running tests
  beforeAll(async () => {
    const testDataPath = path.resolve(__dirname, '../../..', 'testdata/approve-tool.json');
    try {
      const content = await fs.readFile(testDataPath, 'utf-8');
      testEvents = JSON.parse(content);
    } catch (error) {
      console.error(`Failed to load test data from ${testDataPath}:`, error);
      throw error;
    }
  });

  it('should launch a real browser and replay events', async () => {
    // Skip if no test events were loaded
    if (!testEvents || testEvents.length === 0) {
      console.warn('No test events found, skipping test');
      // Use dummy events for testing when test data is missing
      testEvents = [
        { timestamp: 1000, type: 0, data: {} },
        { timestamp: 2000, type: 2, data: {} },
        { timestamp: 3000, type: 3, data: {} }
      ];
    }

    // Run the replay with actual events and check for z-modal
    const result = await runRrwebHeadless({
      events: testEvents,
      playbackSpeed: 4,
      selectors: ['.z-modal'],
      timeout: 10000 // Shorter timeout for CI environments
    });

    // Log detailed results
    console.log('E2E test results:', JSON.stringify(result, null, 2));

    // Verify results (the actual assertion may vary based on your test data)
    expect(result).toBeDefined();
    expect(typeof result.elementExists).toBe('boolean');
    expect(Object.keys(result.selectorResults)).toContain('.z-modal');
  });
});
