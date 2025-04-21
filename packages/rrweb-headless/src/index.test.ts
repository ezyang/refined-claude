import { describe, it, expect, vi, beforeEach } from 'vitest';
import { runRrwebHeadless, loadEventsFromFile, runTestData } from './index';
import type { eventWithTime } from 'rrweb/typings/types';

// Mock modules
vi.mock('fs/promises', async () => {
  return {
    default: {
      readFile: vi.fn().mockResolvedValue(JSON.stringify([
        { timestamp: 1000, type: 0, data: {} },
        { timestamp: 2000, type: 2, data: {} },
        { timestamp: 3000, type: 3, data: {} }
      ]))
    },
    readFile: vi.fn().mockResolvedValue(JSON.stringify([
      { timestamp: 1000, type: 0, data: {} },
      { timestamp: 2000, type: 2, data: {} },
      { timestamp: 3000, type: 3, data: {} }
    ]))
  };
});

vi.mock('playwright', async () => {
  const mockEvaluate = vi.fn();
  mockEvaluate.mockImplementation(() => true);

  const mockPage = {
    setContent: vi.fn().mockResolvedValue(undefined),
    waitForTimeout: vi.fn().mockResolvedValue(undefined),
    evaluate: mockEvaluate
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

      // Get the mocked chromium
      const { chromium } = await import('playwright');

      expect(chromium.launch).toHaveBeenCalledWith({ headless: true });
      expect(result).toEqual({
        elementExists: true,
        selectorResults: {
          '.z-modal': true
        }
      });
    });

    it('should handle multiple selectors', async () => {
      // Override the mock for this test to return different values for different selectors
      const { chromium } = await import('playwright');
      const mockBrowser = await chromium.launch();
      const mockContext = await mockBrowser.newContext();
      const mockPage = await mockContext.newPage();

      // Update the evaluate mock to check the selector
      mockPage.evaluate.mockImplementation((fn, selector) => {
        return selector === '.z-modal';
      });

      const events: eventWithTime[] = [
        { timestamp: 1000, type: 0, data: {} } as any,
        { timestamp: 2000, type: 2, data: {} } as any,
        { timestamp: 3000, type: 3, data: {} } as any
      ];

      const result = await runRrwebHeadless({
        events,
        playbackSpeed: 4,
        selectors: ['.z-modal', '.non-existent']
      });

      expect(result.elementExists).toBe(false);
      expect(result.selectorResults['.z-modal']).toBe(true);
      expect(result.selectorResults['.non-existent']).toBe(false);
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
