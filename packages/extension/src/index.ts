// Content script for the Chrome extension
// This script runs in the context of web pages and looks for .z-modal elements

console.log('[CONTENT] Sublime Claude content script loaded! URL:', window.location.href);

// Import response state observer
import { setupResponseStateObserver } from './observers/responseStateObserver';

// Class to check if we're running in rrweb replay environment
const RRWEB_REPLAY_MARKER = 'rrweb-replay-environment';

// Extension state
interface ExtensionState {
  isRrwebReplay: boolean;
  pageFullyLoaded: boolean;
  autoContinueEnabled: boolean;
}

// Initialize state
const state: ExtensionState = {
  isRrwebReplay: false,
  pageFullyLoaded: false,
  autoContinueEnabled: true, // Default value, will be updated from storage
};

/**
 * Check if the current environment is an rrweb replay
 *
 * This checks if the *current window* is an rrweb replay environment.
 * For iframes inside replays, use the isIframeInRrwebReplay check in init() instead.
 */
function checkIfRrwebReplay(): boolean {
  // Check for specific elements or attributes that indicate rrweb replay
  const hasRrwebElements =
    !!document.getElementById('replay') ||
    !!document.querySelector('.replayer-wrapper') ||
    !!document.querySelector('.replayer-mirror');

  // Look for our internal markers from the test environment
  const hasTestMarkers = !!document.body.getAttribute('data-rrweb-test');

  // Also check if we have our custom class marker
  const hasMarkerClass = document.documentElement.classList.contains(RRWEB_REPLAY_MARKER);

  return hasRrwebElements || hasTestMarkers || hasMarkerClass;
}

/**
 * Find and click the "Allow for this chat" button in a modal
 */
function findAndClickAllowButton(): void {
  // Find the modal
  const modal = document.querySelector('.z-modal');
  if (!modal) return;

  // Log for debugging
  console.log('[CONTENT] Found z-modal:', modal);

  // Look for the button that contains "Allow for this chat" text
  const allowButton = Array.from(modal.querySelectorAll('button')).find(button =>
    button.textContent?.includes('Allow for this chat')
  );

  if (allowButton) {
    console.log('[CONTENT] Clicking "Allow for this chat" button:', allowButton);
    if (!state.isRrwebReplay) {
      allowButton.click();
    } else {
      console.log('[CONTENT] Skipped click due to rrweb replay');
    }
  } else {
    console.log('[CONTENT] Could not find "Allow for this chat" button in modal');
  }
}

/**
 * Find and click the "Continue" button when it appears after page load
 */
function findAndClickContinueButton(): void {
  // Look for the button with the specific class attributes as described
  const continueButton = document.querySelector(
    'button.inline-flex.items-center.justify-center.relative.shrink-0.can-focus.select-none[aria-label="Continue"]'
  );

  if (!continueButton) return;

  // Log for debugging
  console.log('[CONTENT] Found Continue button:', continueButton);

  // Only click if we're not in rrweb replay mode and Auto Continue is enabled
  if (!state.isRrwebReplay && state.autoContinueEnabled) {
    // We don't want to click if this button was present during initial page load
    if (state.pageFullyLoaded) {
      console.log('[CONTENT] Clicking "Continue" button');
      (continueButton as HTMLButtonElement).click();
    } else {
      console.log('[CONTENT] Continue button found during page load, not clicking');
    }
  } else if (!state.autoContinueEnabled) {
    console.log('[CONTENT] Auto Continue is disabled, not clicking Continue button');
  } else {
    console.log('[CONTENT] Skipped Continue button click due to rrweb replay');
  }
}

/**
 * Set up MutationObserver to watch for modal elements
 */
function setupModalObserver(): void {
  // Create a MutationObserver to watch for changes in the DOM
  const observer = new MutationObserver(mutations => {
    // Check if we need to look for the modal after DOM changes
    const shouldCheck = mutations.some(mutation => {
      // If nodes were added, check if any of them have the class or contain elements with the class
      if (mutation.addedNodes.length > 0) {
        for (const node of Array.from(mutation.addedNodes)) {
          if (node instanceof HTMLElement) {
            if (node.classList?.contains('z-modal') || node.querySelector('.z-modal')) {
              return true;
            }
          }
        }
      }

      // If attributes were changed, check if the class was added
      if (
        mutation.type === 'attributes' &&
        mutation.attributeName === 'class' &&
        mutation.target instanceof HTMLElement
      ) {
        return mutation.target.classList.contains('z-modal');
      }

      return false;
    });

    if (shouldCheck) {
      findAndClickAllowButton();
    }
  });

  // Configure the observer to watch for additions of nodes and changes to class attributes
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['class'],
  });

  console.log('[CONTENT] Modal observer set up');
}

/**
 * Set up MutationObserver to watch for "Continue" button
 */
function setupContinueButtonObserver(): void {
  // Create a MutationObserver to watch for changes in the DOM
  const observer = new MutationObserver(mutations => {
    // Check if any nodes were added or attributes were changed
    const buttonsAdded = mutations.some(mutation => {
      // Check for button elements in added nodes
      if (mutation.addedNodes.length > 0) {
        for (const node of Array.from(mutation.addedNodes)) {
          if (node instanceof HTMLElement) {
            // Check if this node is the button we're looking for
            if (node.tagName === 'BUTTON' && node.getAttribute('aria-label') === 'Continue') {
              return true;
            }

            // Or if it contains the button we're looking for
            const button = node.querySelector('button[aria-label="Continue"]');
            if (button) {
              return true;
            }
          }
        }
      }

      // Check if attributes changed on a button element
      if (
        mutation.type === 'attributes' &&
        mutation.target instanceof HTMLElement &&
        mutation.target.tagName === 'BUTTON'
      ) {
        if (mutation.target.getAttribute('aria-label') === 'Continue') {
          return true;
        }
      }

      return false;
    });

    if (buttonsAdded) {
      findAndClickContinueButton();
    }
  });

  // Configure the observer to watch for additions of nodes and changes to attributes
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['aria-label', 'class'],
  });

  console.log('[CONTENT] Continue button observer set up');
}

/**
 * Set up MutationObserver to watch for iframe elements in rrweb replay
 */
function setupIframeObserver(): void {
  console.log('[CONTENT] Setting up iframe observer for rrweb replay');

  // Maintain a record of processed iframes to avoid duplicates
  const processedIframes = new Set<string>();

  // Create a MutationObserver to watch for iframe additions to the DOM
  const observer = new MutationObserver(mutations => {
    for (const mutation of mutations) {
      if (mutation.addedNodes.length > 0) {
        for (const node of Array.from(mutation.addedNodes)) {
          if (node instanceof HTMLIFrameElement) {
            injectContentScriptIntoIframe(node, processedIframes);
          } else if (node instanceof HTMLElement) {
            // Check for iframes within the added node
            const iframes = node.querySelectorAll('iframe');
            iframes.forEach(iframe => injectContentScriptIntoIframe(iframe, processedIframes));
          }
        }
      }
    }
  });

  // Configure the observer to watch for additions of nodes
  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });

  // Also check for any existing iframes
  const existingIframes = document.querySelectorAll('iframe');
  existingIframes.forEach(iframe => injectContentScriptIntoIframe(iframe, processedIframes));

  console.log('[CONTENT] Iframe observer set up');
}

/**
 * Inject the content script into an iframe using the background script
 */
function injectContentScriptIntoIframe(
  iframe: HTMLIFrameElement,
  processedIframes: Set<string>
): void {
  // Generate a unique identifier for the iframe
  let iframeId: string;
  try {
    // Try to use src as identifier if available
    iframeId = iframe.src || `iframe-${Math.random().toString(36).substring(2, 11)}`;
  } catch (e) {
    // Fallback to random ID if we can't access src (e.g., cross-origin)
    iframeId = `iframe-${Math.random().toString(36).substring(2, 11)}`;
  }

  // Skip if we've already processed this iframe
  if (processedIframes.has(iframeId)) {
    console.log('[CONTENT] Content script already processed for this iframe:', iframeId);
    return;
  }

  console.log('[CONTENT] Attempting to inject content script into iframe:', iframeId);

  // Mark this iframe as processed
  processedIframes.add(iframeId);

  // Ensure the iframe is loaded before trying to inject scripts
  if (!iframe.contentWindow) {
    console.log('[CONTENT] Iframe not fully loaded yet, setting up load listener');
    iframe.addEventListener('load', () => {
      injectContentScriptIntoIframe(iframe, processedIframes);
    });
    return;
  }

  try {
    // Add a unique identifier to the iframe to target it later
    const frameSelector = `frame-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    iframe.setAttribute('data-extension-frame-id', frameSelector);

    // First get the current tab ID
    chrome.runtime.sendMessage({ action: 'getTabInfo' }, response => {
      if (chrome.runtime.lastError) {
        console.error('Error getting tab info:', chrome.runtime.lastError);
        return;
      }

      if (response.error) {
        console.error('Error from background script:', response.error);
        return;
      }

      const tabId = response.tabId;
      console.log('[CONTENT] Got tab ID:', tabId, 'for iframe injection');

      // Now ask the background script to inject into the specific frame
      chrome.runtime.sendMessage(
        {
          action: 'injectScriptIntoFrame',
          tabId,
          frameSelector,
        },
        injectionResponse => {
          if (chrome.runtime.lastError) {
            console.error('Error during script injection:', chrome.runtime.lastError);
            return;
          }

          if (injectionResponse.error) {
            console.error('Injection error from background script:', injectionResponse.error);
          } else {
            console.log('[CONTENT] Successfully injected script into iframe:', injectionResponse);
          }
        }
      );
    });
  } catch (error) {
    console.error('Error during iframe content script injection setup:', error);
  }
}

/**
 * Check if the current frame is an iframe inside an rrweb replay environment
 */
function isIframeInsideRrwebReplay(): boolean {
  // If we're a top-level window, we're not an iframe in a replay
  if (window.self === window.top) {
    return false;
  }

  // Check if the parent window shows signs of being a replay environment
  try {
    return !!(
      window.parent &&
      (window.parent.document.getElementById('replay') ||
        window.parent.document.querySelector('.replayer-wrapper') ||
        window.parent.document.querySelector('.replayer-mirror') ||
        window.parent.document.body.getAttribute('data-rrweb-test') ||
        window.parent.document.documentElement.classList.contains(RRWEB_REPLAY_MARKER))
    );
  } catch (e) {
    // If we can't access the parent due to cross-origin restrictions
    console.log('[CONTENT] Cannot access parent frame, assuming not in replay:', e);
    return false;
  }
}

/**
 * Load extension settings from chrome.storage.sync
 */
async function loadSettings(): Promise<void> {
  try {
    // Get the current settings from chrome.storage.sync
    const result = await new Promise<{ autoContinueEnabled: boolean }>(resolve => {
      chrome.storage.sync.get({ autoContinueEnabled: true }, items => {
        if (chrome.runtime.lastError) {
          console.error('[CONTENT] Error loading settings:', chrome.runtime.lastError);
          // Use default values if there's an error
          resolve({ autoContinueEnabled: true });
          return;
        }
        resolve(items as { autoContinueEnabled: boolean });
      });
    });

    // Update the state with the loaded settings
    state.autoContinueEnabled = result.autoContinueEnabled;
    console.log('[CONTENT] Settings loaded:', result);
  } catch (error) {
    console.error('[CONTENT] Error in loadSettings:', error);
    // If there's an error, use default values
    state.autoContinueEnabled = true;
  }
}

/**
 * Initialize the extension
 */
async function init(): Promise<void> {
  console.log('[CONTENT] Sublime Claude Modal Auto-Clicker extension initialized');

  // Load settings first
  await loadSettings();

  // Check if we're in an rrweb replay environment
  state.isRrwebReplay = checkIfRrwebReplay();
  console.log('[CONTENT] Running in rrweb replay mode:', state.isRrwebReplay);

  // Logic is reversed: the content script should run in iframes inside rrweb replay,
  // not in the top level rrweb replay environment itself
  const isIframeInReplay = isIframeInsideRrwebReplay();
  console.log('[CONTENT] Is iframe inside rrweb replay:', isIframeInReplay);

  // Set up message listener for settings updates
  chrome.runtime.onMessage.addListener((message, _sender, _sendResponse) => {
    if (message.action === 'updateSettings' && message.settings) {
      console.log('[CONTENT] Received settings update:', message.settings);
      // Update the state with new settings
      if (message.settings.autoContinueEnabled !== undefined) {
        state.autoContinueEnabled = message.settings.autoContinueEnabled;
      }
    }
  });

  // Only continue if:
  // 1. This is NOT a top-level rrweb replay environment, OR
  // 2. This is an iframe INSIDE an rrweb replay environment
  if (!state.isRrwebReplay || isIframeInReplay) {
    // Set up observer for future changes
    setupModalObserver();

    // Set up Continue button observer
    setupContinueButtonObserver();

    // Set up response state observer
    setupResponseStateObserver();

    // Set pageFullyLoaded flag after the page has loaded
    if (document.readyState === 'complete') {
      state.pageFullyLoaded = true;
      console.log('[CONTENT] Page is already fully loaded');
    } else {
      window.addEventListener('load', () => {
        state.pageFullyLoaded = true;
        console.log('[CONTENT] Page fully loaded event fired');

        // Check once for the Continue button after page load
        findAndClickContinueButton();
      });
    }
  } else {
    console.log('[CONTENT] Skipping modal observer setup in top-level rrweb replay environment');

    // In top-level rrweb replay environment, we need to inject our script into iframes
    setupIframeObserver();
  }
}

// Start the extension
init();

// Export for testing
export {
  findAndClickAllowButton,
  findAndClickContinueButton,
  setupContinueButtonObserver,
  checkIfRrwebReplay,
  isIframeInsideRrwebReplay,
  injectContentScriptIntoIframe,
  setupResponseStateObserver,
  loadSettings,
};
