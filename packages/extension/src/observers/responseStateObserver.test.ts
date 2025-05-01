import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { setupResponseStateObserver } from './responseStateObserver';

describe('responseStateObserver', () => {
  // Setup mocks
  beforeEach(() => {
    // Mock console.log
    vi.spyOn(console, 'log').mockImplementation(() => {});

    // Mock chrome.runtime.sendMessage
    global.chrome = {
      runtime: {
        sendMessage: vi.fn((message, callback) => {
          if (callback) {
            callback({ success: true });
          }
          return true;
        }),
      },
    } as any;

    // Create a clean DOM environment for each test
    document.body.innerHTML = '';
  });

  // Cleanup after each test
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should detect when a button transitions from RUNNING to STOPPED state', () => {
    // Initialize the observer
    setupResponseStateObserver();

    // Create a button in RUNNING state
    const button = document.createElement('button');
    button.setAttribute('aria-label', 'Stop response');
    button.className =
      'inline-flex items-center justify-center relative shrink-0 can-focus select-none disabled:pointer-events-none disabled:opacity-50 disabled:shadow-none disabled:drop-shadow-none text-text-000 border-0.5 border-border-300 relative overflow-hidden font-styrene font-medium transition duration-100 hover:border-border-300/0 bg-bg-300/0 hover:bg-bg-400 backface-hidden h-8 w-8 rounded-md active:scale-95 !rounded-lg';
    button.innerHTML =
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 256 256"><path d="M128,20A108,108,0,1,0,236,128,108.12,108.12,0,0,0,128,20Zm0,192a84,84,0,1,1,84-84A84.09,84.09,0,0,1,128,212Zm40-112v56a12,12,0,0,1-12,12H100a12,12,0,0,1-12-12V100a12,12,0,0,1,12-12h56A12,12,0,0,1,168,100Z"></path></svg>';

    // Add the button to the DOM
    document.body.appendChild(button);

    // Verify that the observer detects and starts tracking the button
    expect(console.log).toHaveBeenCalledWith(
      expect.stringContaining('Tracking button in state: RUNNING')
    );

    // Change the button to STOPPED state
    button.setAttribute('aria-label', 'Send message');
    button.className =
      'inline-flex items-center justify-center relative shrink-0 can-focus select-none disabled:pointer-events-none disabled:opacity-50 disabled:shadow-none disabled:drop-shadow-none bg-accent-main-000 text-oncolor-100 font-styrene font-medium transition-colors hover:bg-accent-main-200 h-8 w-8 rounded-md active:scale-95 !rounded-lg !h-8 !w-8';
    button.innerHTML =
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 256 256"><path d="M208.49,120.49a12,12,0,0,1-17,0L140,69V216a12,12,0,0,1-24,0V69L64.49,120.49a12,12,0,0,1-17-17l72-72a12,12,0,0,1,17,0l72,72A12,12,0,0,1,208.49,120.49Z"></path></svg>';

    // Simulate attribute change event
    const mutationEvent = new MutationEvent();
    mutationEvent.initMutationEvent(
      'DOMAttrModified',
      true,
      false,
      null,
      '',
      'aria-label',
      'Stop response',
      'Send message'
    );
    button.dispatchEvent(mutationEvent);

    // Verify that the observer detects the state change
    expect(console.log).toHaveBeenCalledWith(
      expect.stringContaining('Response state changed: RUNNING → STOPPED')
    );

    // Verify notification was sent
    expect(chrome.runtime.sendMessage).toHaveBeenCalledWith({
      action: 'showNotification',
      title: 'Claude Response Complete',
      message: 'Your Claude response has finished generating.',
    });
  });

  it('should not send a notification when button is first observed in STOPPED state', () => {
    // Initialize the observer
    setupResponseStateObserver();

    // Create a button in STOPPED state (not transitioning from RUNNING)
    const button = document.createElement('button');
    button.setAttribute('aria-label', 'Send message');
    button.className =
      'inline-flex items-center justify-center relative shrink-0 can-focus select-none disabled:pointer-events-none disabled:opacity-50 disabled:shadow-none disabled:drop-shadow-none bg-accent-main-000 text-oncolor-100 font-styrene font-medium transition-colors hover:bg-accent-main-200 h-8 w-8 rounded-md active:scale-95 !rounded-lg !h-8 !w-8';
    button.innerHTML =
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 256 256"><path d="M208.49,120.49a12,12,0,0,1-17,0L140,69V216a12,12,0,0,1-24,0V69L64.49,120.49a12,12,0,0,1-17-17l72-72a12,12,0,0,1,17,0l72,72A12,12,0,0,1,208.49,120.49Z"></path></svg>';

    // Add the button to the DOM
    document.body.appendChild(button);

    // Verify that the observer tracks the button
    expect(console.log).toHaveBeenCalledWith(
      expect.stringContaining('Tracking button in state: STOPPED')
    );

    // Verify no notification was sent (since it didn't transition from RUNNING to STOPPED)
    expect(chrome.runtime.sendMessage).not.toHaveBeenCalled();
  });
});
