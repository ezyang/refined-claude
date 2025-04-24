/**
 * Shared module for modal dialog observer functionality
 * Used by both content script and injected content script
 */

/**
 * Find and click the "Allow for this chat" button in a modal
 *
 * @param isTestMode If true, will create a marker instead of clicking the button
 * @param logPrefix Prefix for console logs (e.g., '[CONTENT]' or '[I-CONTENT]')
 * @returns True if button was found, false otherwise
 */
export function findAndClickAllowButton(isTestMode = false, logPrefix = '[MODAL]'): boolean {
  // Find the modal
  const modal = document.querySelector('.z-modal');
  if (!modal) return false;

  // Log for debugging
  console.log(`${logPrefix} Found z-modal:`, modal);

  // Look for the button that contains "Allow for this chat" text
  const allowButton = Array.from(modal.querySelectorAll('button'))
    .find(button => button.textContent?.includes('Allow for this chat'));

  if (allowButton) {
    console.log(`${logPrefix} Found "Allow for this chat" button:`, allowButton);

    if (isTestMode) {
      // In test mode, don't actually click but mark for testing
      console.log(`${logPrefix} Test mode: Would click "Allow for this chat" button`);

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
      console.log(`${logPrefix} Clicking "Allow for this chat" button`);
      allowButton.click();
    }
    return true;
  } else {
    console.log(`${logPrefix} Could not find "Allow for this chat" button in modal`);
    return false;
  }
}

/**
 * Set up MutationObserver to watch for modal elements
 *
 * @param onModalFound Function to call when a modal is found
 * @param logPrefix Prefix for console logs
 * @returns The created MutationObserver
 */
export function setupModalObserver(
  onModalFound: () => void,
  logPrefix = '[MODAL]'
): MutationObserver {
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
      onModalFound();
    }
  });

  // Configure the observer to watch for additions of nodes and changes to class attributes
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['class']
  });

  console.log(`${logPrefix} Modal observer set up`);
  return observer;
}

// Expose functions globally when used as a direct script injection
// This allows them to be called from the injected script context
window.findAndClickAllowButton = findAndClickAllowButton;
window.setupModalObserver = setupModalObserver;
