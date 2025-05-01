// Observer for detecting when a response button toggles between RUNNING and STOPPED states

/**
 * The states the response button can be in
 */
enum ResponseButtonState {
  RUNNING = 'RUNNING',
  STOPPED = 'STOPPED',
}

/**
 * Check if a button element is in the RUNNING state based on its attributes
 *
 * RUNNING state has these characteristics:
 * - aria-label="Stop response"
 * - Contains a specific SVG path for the stop icon
 * - Has specific CSS classes including border styles
 */
function isButtonInRunningState(button: HTMLButtonElement): boolean {
  return (
    button.getAttribute('aria-label') === 'Stop response' &&
    button.classList.contains('border-border-300') && // Added specific class check if needed
    button.querySelector('svg path[d*="M128,20A108,108,0,1,0,236,128"]') !== null
  );
}

/**
 * Check if a button element is in the STOPPED state based on its attributes
 *
 * STOPPED state has these characteristics:
 * - aria-label="Send message"
 * - Contains a specific SVG path for the up arrow icon
 * - Has specific CSS classes including accent color
 */
function isButtonInStoppedState(button: HTMLButtonElement): boolean {
  return (
    button.getAttribute('aria-label') === 'Send message' &&
    button.classList.contains('bg-accent-main-000') && // Added specific class check if needed
    button.querySelector('svg path[d*="M208.49,120.49a12,12,0"]') !== null
  );
}

// Global state for the *overall* response state detected in the DOM
let currentOverallState: ResponseButtonState | null = null;

/**
 * Queries the DOM to determine the current response state based on available buttons.
 * Updates the global state and triggers notifications on specific transitions.
 */
function evaluateCurrentResponseState() {
  let detectedState: ResponseButtonState | null = null;

  // Prioritize checking for the RUNNING state
  // QuerySelectorAll might be safer if multiple could exist transiently
  const potentialRunningButtons = document.querySelectorAll('button[aria-label="Stop response"]');
  for (const btn of potentialRunningButtons) {
    // Ensure it's attached to the DOM before checking state
    if (document.body.contains(btn) && isButtonInRunningState(btn as HTMLButtonElement)) {
      detectedState = ResponseButtonState.RUNNING;
      break; // Found a valid running button, this is the definitive state
    }
  }

  // If no RUNNING button was found, check for STOPPED state
  if (detectedState === null) {
    const potentialStoppedButtons = document.querySelectorAll('button[aria-label="Send message"]');
    for (const btn of potentialStoppedButtons) {
      // Ensure it's attached to the DOM before checking state
      if (document.body.contains(btn) && isButtonInStoppedState(btn as HTMLButtonElement)) {
        detectedState = ResponseButtonState.STOPPED;
        break; // Found a valid stopped button
      }
    }
  }

  // Compare detectedState with the last known overall state
  if (currentOverallState !== detectedState) {
    console.log(
      `[CONTENT] Response state changed: ${currentOverallState ?? 'UNKNOWN'} → ${detectedState ?? 'UNKNOWN'}`
    );

    // Trigger notification specifically for RUNNING -> STOPPED transition
    if (
      currentOverallState === ResponseButtonState.RUNNING &&
      detectedState === ResponseButtonState.STOPPED
    ) {
      console.log('[CONTENT] Sending Response Complete notification.');
      // Use try-catch for message sending as context might become invalid
      try {
        chrome.runtime.sendMessage({
          action: 'showNotification',
          title: 'Claude Response Complete',
          message: 'Your Claude response has finished generating.',
        });
      } catch (error) {
        console.error('[CONTENT] Error sending notification:', error);
      }
    }

    // Update the tracked state
    currentOverallState = detectedState;
  }
}

/**
 * Setup an observer to detect when the response button toggles between RUNNING and STOPPED
 */
export function setupResponseStateObserver(): void {
  console.log('[CONTENT] Setting up response state observer v2');

  // Debounce function to avoid rapid firing during DOM updates
  let debounceTimeout: number | null = null;
  const debouncedEvaluate = () => {
    if (debounceTimeout) clearTimeout(debounceTimeout);
    debounceTimeout = window.setTimeout(() => {
      evaluateCurrentResponseState();
      debounceTimeout = null;
    }, 150); // Increased debounce slightly
  };

  // Create a MutationObserver to watch for relevant DOM changes
  const observer = new MutationObserver(mutations => {
    // Instead of analyzing each mutation deeply, simply re-evaluate on relevant changes.
    // Check if any mutation might affect buttons we care about.
    let relevantChange = false;
    for (const mutation of mutations) {
      // Attribute changes on buttons or their children are relevant
      if (mutation.type === 'attributes') {
        if (mutation.target instanceof HTMLButtonElement || mutation.target.closest('button')) {
          // Check if the specific attribute change is potentially relevant
          if (
            mutation.attributeName === 'class' ||
            mutation.attributeName === 'aria-label' ||
            mutation.attributeName === 'disabled'
          ) {
            relevantChange = true;
            break;
          }
        }
      }
      // Child list changes (nodes added/removed) anywhere could potentially add/remove/modify the button
      if (mutation.type === 'childList') {
        relevantChange = true;
        break;
      }
    }

    if (relevantChange) {
      debouncedEvaluate();
    }
  });

  // Function to perform the initial state check
  const performInitialCheck = () => {
    // Use setTimeout to ensure the DOM is likely settled after load/initial script run
    console.log('[CONTENT] Performing initial response state check...');
    // Clear any previous state before the first check
    currentOverallState = null;
    setTimeout(evaluateCurrentResponseState, 300); // Slightly longer delay for initial check
  };

  // Configure the observer to watch the document body for relevant changes
  observer.observe(document.body, {
    childList: true, // Watch for nodes being added or removed
    subtree: true, // Watch descendants too
    attributes: true, // Watch for attribute changes
    attributeFilter: ['class', 'aria-label', 'disabled'], // Focus on attributes likely to change button state appearance/identity
    characterData: false, // Don't need character data changes
  });

  // Perform the initial check once the document is ready
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    performInitialCheck();
  } else {
    window.addEventListener('DOMContentLoaded', performInitialCheck); // Use DOMContentLoaded for faster check
  }

  console.log('[CONTENT] Response state observer setup complete v2');
}
