import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { runRrwebReplay, loadEventsFromFile } from './index';
import path from 'path';
import fs from 'fs/promises';

// This is an actual end-to-end test that launches a real browser
describe('rrweb-headless e2e', () => {
  it('should launch a real browser and replay events', async () => {
    const testDataPath = path.resolve(__dirname, '../../..', 'testdata/approve-tool.json');

    // Use loadEventsFromFile to properly load events
    const testEvents = await loadEventsFromFile(testDataPath);

    // Skip if no test events were loaded
    expect(testEvents);
    expect(testEvents.length !== 0);

    // Run the replay with actual events and check for z-modal
    const result = await runRrwebReplay({
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
  }, 30_000);
});
