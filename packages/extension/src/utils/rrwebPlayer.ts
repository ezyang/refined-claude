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

export default {
  markAsRrwebTest,
  checkAllowButtonClicked,
};
