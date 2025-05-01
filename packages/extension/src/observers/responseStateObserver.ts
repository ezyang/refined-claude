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
    button.classList.contains('border-border-300') &&
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
    button.classList.contains('bg-accent-main-000') &&
    button.querySelector('svg path[d*="M208.49,120.49a12,12,0"]') !== null
  );
}

/**
 * Setup an observer to detect when the response button toggles between RUNNING and STOPPED
 */
export function setupResponseStateObserver(): void {
  console.log('[CONTENT] Setting up response state observer');

  // Track the current state of the observed button
  let currentButtonState: ResponseButtonState | null = null;
  let observedButton: HTMLButtonElement | null = null;

  // Function to check for state changes and emit notifications
  const checkButtonStateChange = (button: HTMLButtonElement) => {
    // Determine the new state
    let newState: ResponseButtonState | null = null;

    if (isButtonInRunningState(button)) {
      newState = ResponseButtonState.RUNNING;
    } else if (isButtonInStoppedState(button)) {
      newState = ResponseButtonState.STOPPED;
    }

    // If we can't determine the state, return
    if (newState === null) return;

    // If this is the first time we're seeing this button, just record the state
    if (observedButton === null || currentButtonState === null) {
      observedButton = button;
      currentButtonState = newState;
      console.log(`[CONTENT] Tracking button in state: ${newState}`);
      return;
    }

    // Always update the observed button to the latest one
    // This ensures we track the same button even if DOM elements are recreated
    observedButton = button;

    // Check if the state changed from RUNNING to STOPPED
    if (
      currentButtonState === ResponseButtonState.RUNNING &&
      newState === ResponseButtonState.STOPPED
    ) {
      // State changed from RUNNING to STOPPED - emit notification
      console.log('[CONTENT] Response state changed: RUNNING → STOPPED');

      // Send notification via chrome notifications API
      chrome.runtime.sendMessage({
        action: 'showNotification',
        title: 'Claude Response Complete',
        message: 'Your Claude response has finished generating.',
      });
    }

    // Log state changes for any transition (for debugging)
    if (currentButtonState !== newState) {
      console.log(`[CONTENT] Tracking button in state: ${newState}`);
    }

    // Update the current state
    currentButtonState = newState;
  };

  // Create a MutationObserver to watch for button state changes
  const observer = new MutationObserver(mutations => {
    for (const mutation of mutations) {
      // Check for button elements that match our target in added nodes
      if (mutation.addedNodes.length > 0) {
        for (const node of Array.from(mutation.addedNodes)) {
          if (node instanceof HTMLButtonElement) {
            if (isButtonInRunningState(node) || isButtonInStoppedState(node)) {
              checkButtonStateChange(node);
            }
          } else if (node instanceof HTMLElement) {
            // Check for matching buttons within added nodes
            const buttons = node.querySelectorAll('button');
            buttons.forEach(button => {
              if (
                button instanceof HTMLButtonElement &&
                (isButtonInRunningState(button) || isButtonInStoppedState(button))
              ) {
                checkButtonStateChange(button);
              }
            });
          }
        }
      }

      // Check if attributes changed on a button element we care about
      if (
        mutation.type === 'attributes' &&
        mutation.target instanceof HTMLButtonElement &&
        (mutation.attributeName === 'aria-label' ||
          mutation.attributeName === 'class' ||
          mutation.attributeName === 'disabled')
      ) {
        const button = mutation.target as HTMLButtonElement;
        if (isButtonInRunningState(button) || isButtonInStoppedState(button)) {
          checkButtonStateChange(button);
        }
      }

      // Check for changes to SVG elements inside buttons (icon changes)
      if (
        mutation.type === 'childList' &&
        mutation.target instanceof HTMLElement &&
        (mutation.target.tagName === 'BUTTON' || mutation.target.closest('button') !== null)
      ) {
        const button =
          mutation.target.tagName === 'BUTTON'
            ? (mutation.target as HTMLButtonElement)
            : (mutation.target.closest('button') as HTMLButtonElement);

        if (button && (isButtonInRunningState(button) || isButtonInStoppedState(button))) {
          checkButtonStateChange(button);
        }
      }
    }
  });

  // Initial check for existing buttons
  const checkExistingButtons = () => {
    const buttons = document.querySelectorAll('button');
    buttons.forEach(button => {
      if (
        button instanceof HTMLButtonElement &&
        (isButtonInRunningState(button) || isButtonInStoppedState(button))
      ) {
        checkButtonStateChange(button);
      }
    });
  };

  // Configure the observer to watch for DOM changes
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['aria-label', 'class', 'disabled'],
    characterData: false,
  });

  // Check for existing buttons
  if (document.readyState === 'complete') {
    checkExistingButtons();
  } else {
    window.addEventListener('load', checkExistingButtons);
  }

  console.log('[CONTENT] Response state observer setup complete');
}
