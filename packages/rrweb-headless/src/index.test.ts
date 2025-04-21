import { describe, it, expect, vi, beforeEach } from 'vitest';
import { runRrwebHeadless, loadEventsFromFile, runTestData } from './index';
import type { eventWithTime } from 'rrweb/typings/types';
import { chromium } from 'playwright';

// Mock Playwright
vi.mock('playwright', () => {
  const mockPage = {
    setContent: vi.fn().mockResolvedValue(undefined),
    waitForTimeout: vi.fn().mockResolvedValue(undefined),
    evaluate: vi.fn().mockResolvedValue(true)
  };

  const mockContext = {
    newPage: vi.fn().mockResolvedValue(mockPage)
  };

  const mockBrowser = {
    newContext: vi.fn().mockResolvedValue(mockContext),
    close: vi.fn().mockResolvedValue(undefined)
  };

  return {
    chromium: {
      launch: vi.fn().mockResolvedValue(mockBrowser)
    }
  };
});

// Mock fs/promises
vi.mock('fs/promises', () => ({
  readFile: vi.fn().mockResolvedValue(JSON.stringify([
    { timestamp: 1000, type: 0, data: {} },
    { timestamp: 2000, type: 2, data: {} },
    { timestamp: 3000, type: 3, data: {} }
  ]))
}));

describe('rrweb-headless', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('runRrwebHeadless', () => {
    it('should launch a browser and check selectors', async () => {
      const events: eventWithTime[] = [
        { timestamp: 1000, type: 0, data: {} } as any,
        { timestamp: 2000, type: 2, data: {} } as any,
        { timestamp: 3000, type: 3, data: {} } as any
      ];

      const result = await runRrwebHeadless({
        events,
        playbackSpeed: 4,
        selectors: ['.z-modal']
      });

      expect(chromium.launch).toHaveBeenCalledWith({ headless: true });
      expect(result).toEqual({
        elementExists: true,
        selectorResults: {
          '.z-modal': true
        }
      });
    });

    it('should handle multiple selectors', async () => {
      const events: eventWithTime[] = [
        { timestamp: 1000, type: 0, data: {} } as any,
        { timestamp: 2000, type: 2, data: {} } as any,
        { timestamp: 3000, type: 3, data: {} } as any
      ];

      const page = (await (await (chromium as any).launch()).newContext()).newPage();

      // Make the first selector exist, second one not exist
      page.evaluate.mockImplementation((fn, selector) => {
        return selector === '.z-modal';
      });

      const result = await runRrwebHeadless({
        events,
        playbackSpeed: 4,
        selectors: ['.z-modal', '.non-existent']
      });

      expect(result).toEqual({
        elementExists: false,
        selectorResults: {
          '.z-modal': true,
          '.non-existent': false
        }
      });
    });
  });

  describe('loadEventsFromFile', () => {
    it('should load events from a file', async () => {
      const events = await loadEventsFromFile('fake-path.json');
      expect(events).toHaveLength(3);
      expect(events[0].timestamp).toBe(1000);
    });
  });

  describe('runTestData', () => {
    it('should run the test data file', async () => {
      const result = await runTestData();
      expect(result.elementExists).toBe(true);
    });
  });
});
