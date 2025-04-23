// Content script for the Chrome extension
// This script runs in the context of web pages and looks for .z-modal elements

console.log('Sublime Claude content script loaded! URL:', window.location.href);

// Class to check if we're running in rrweb replay environment
const RRWEB_REPLAY_MARKER = 'rrweb-replay-environment';

// Extension state
interface ExtensionState {
  isRrwebReplay: boolean;
}

// Initialize state
const state: ExtensionState = {
  isRrwebReplay: false
};

/**
 * Check if the current environment is an rrweb replay
 *
 * This checks if the *current window* is an rrweb replay environment.
 * For iframes inside replays, use the isIframeInRrwebReplay check in init() instead.
 */
function checkIfRrwebReplay(): boolean {
  // Check for specific elements or attributes that indicate rrweb replay
  const hasRrwebElements = !!document.getElementById('replay') ||
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
  console.log('Found z-modal:', modal);

  // Look for the button that contains "Allow for this chat" text
  const allowButton = Array.from(modal.querySelectorAll('button'))
    .find(button => button.textContent?.includes('Allow for this chat'));

  if (allowButton) {
    console.log('Found "Allow for this chat" button:', allowButton);

    if (state.isRrwebReplay) {
      // In test mode, don't actually click but mark for testing
      console.log('Test mode: Would click "Allow for this chat" button');

      // Create a marker element that doesn't affect page layout
      const marker = document.createElement('div');
      marker.id = 'allow-button-clicked-marker';
      marker.style.display = 'none';
      marker.style.position = 'absolute';
      marker.style.top = '-9999px';
      marker.style.left = '-9999px';
      marker.style.zIndex = '-1';
      marker.style.pointerEvents = 'none';
      marker.setAttribute('data-button-text', allowButton.textContent || 'Allow for this chat');

      // Append to an existing non-visual element if possible or to body as a last resort
      const container = document.head || document.body;
      container.appendChild(marker);
    } else {
      // In normal mode, actually click the button
      console.log('Clicking "Allow for this chat" button');
      allowButton.click();
    }
  } else {
    console.log('Could not find "Allow for this chat" button in modal');
  }
}

/**
 * Set up MutationObserver to watch for modal elements
 */
function setupModalObserver(): void {
  // Create a MutationObserver to watch for changes in the DOM
  const observer = new MutationObserver((mutations) => {
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
      if (mutation.type === 'attributes' &&
          mutation.attributeName === 'class' &&
          mutation.target instanceof HTMLElement) {
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
    attributeFilter: ['class']
  });

  console.log('Modal observer set up');
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
    return !!(window.parent && (
      window.parent.document.getElementById('replay') ||
      window.parent.document.querySelector('.replayer-wrapper') ||
      window.parent.document.querySelector('.replayer-mirror') ||
      window.parent.document.body.getAttribute('data-rrweb-test') ||
      window.parent.document.documentElement.classList.contains(RRWEB_REPLAY_MARKER)
    ));
  } catch (e) {
    // If we can't access the parent due to cross-origin restrictions
    console.log('Cannot access parent frame, assuming not in replay:', e);
    return false;
  }
}

/**
 * Initialize the extension
 */
function init(): void {
  console.log('Sublime Claude Modal Auto-Clicker extension initialized');

  // Check if we're in an rrweb replay environment
  state.isRrwebReplay = checkIfRrwebReplay();
  console.log('Running in rrweb replay mode:', state.isRrwebReplay);

  // Logic is reversed: the content script should run in iframes inside rrweb replay,
  // not in the top level rrweb replay environment itself
  const isIframeInReplay = isIframeInsideRrwebReplay();
  console.log('Is iframe inside rrweb replay:', isIframeInReplay);

  // Only continue if:
  // 1. This is NOT a top-level rrweb replay environment, OR
  // 2. This is an iframe INSIDE an rrweb replay environment
  if (!state.isRrwebReplay || isIframeInReplay) {
    // Set up observer for future changes
    setupModalObserver();
  } else {
    console.log('Skipping observer setup in top-level rrweb replay environment');
  }
}

// Start the extension
init();

// Export for testing
export { findAndClickAllowButton, checkIfRrwebReplay, isIframeInsideRrwebReplay };
