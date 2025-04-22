/**
 * Utility functions for working with rrweb player in test environments
 */

/**
 * Mark the document as an rrweb test environment
 * This allows the extension to detect it's running in a test
 */
export function markAsRrwebTest(): void {
  if (typeof document !== 'undefined') {
    document.body.setAttribute('data-rrweb-test', 'true');
  }
}

/**
 * Check if the extension detected and would click a button
 * Returns the text of the button that would be clicked, or null if no button was detected
 */
export function checkAllowButtonClicked(): string | null {
  if (typeof document === 'undefined') return null;

  const marker = document.getElementById('allow-button-clicked-marker');
  if (marker) {
    return marker.getAttribute('data-button-text');
  }
  return null;
}

/**
 * Create a test modal with an "Allow for this chat" button
 * Useful for testing the extension without actual modals
 */
export function createTestModal(): HTMLElement {
  if (typeof document === 'undefined') {
    throw new Error('Document is not available');
  }

  // Create modal container
  const modal = document.createElement('div');
  modal.className = 'z-modal';
  modal.style.position = 'fixed';
  modal.style.top = '0';
  modal.style.left = '0';
  modal.style.width = '100%';
  modal.style.height = '100%';
  modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
  modal.style.display = 'flex';
  modal.style.justifyContent = 'center';
  modal.style.alignItems = 'center';
  modal.style.zIndex = '9999';

  // Create modal content
  const content = document.createElement('div');
  content.style.backgroundColor = 'white';
  content.style.padding = '20px';
  content.style.borderRadius = '8px';
  content.style.maxWidth = '400px';

  // Create title
  const title = document.createElement('h2');
  title.textContent = 'Allow Access';

  // Create description
  const description = document.createElement('p');
  description.textContent = 'This application is requesting permission to access your data.';

  // Create buttons container
  const buttons = document.createElement('div');
  buttons.style.display = 'flex';
  buttons.style.justifyContent = 'flex-end';
  buttons.style.marginTop = '20px';

  // Create cancel button
  const cancelButton = document.createElement('button');
  cancelButton.textContent = 'Cancel';
  cancelButton.style.marginRight = '10px';

  // Create allow button
  const allowButton = document.createElement('button');
  allowButton.textContent = 'Allow for this chat';
  allowButton.style.backgroundColor = '#0056b3';
  allowButton.style.color = 'white';
  allowButton.style.border = 'none';
  allowButton.style.padding = '8px 16px';
  allowButton.style.borderRadius = '4px';

  // Assemble the modal
  buttons.appendChild(cancelButton);
  buttons.appendChild(allowButton);

  content.appendChild(title);
  content.appendChild(description);
  content.appendChild(buttons);

  modal.appendChild(content);

  // Add to document
  document.body.appendChild(modal);

  return modal;
}

/**
 * Remove a test modal from the document
 */
export function removeTestModal(modal: HTMLElement): void {
  if (modal && modal.parentNode) {
    modal.parentNode.removeChild(modal);
  }
}

export default {
  markAsRrwebTest,
  checkAllowButtonClicked,
  createTestModal,
  removeTestModal
};
