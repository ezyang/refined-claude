import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { findAndClickAllowButton, checkIfRrwebReplay } from './index';
import { createTestModal, removeTestModal, markAsRrwebTest, checkAllowButtonClicked } from './utils/rrwebPlayer';

// Mock MutationObserver for test environment
global.MutationObserver = class {
  observe() {}
  disconnect() {}
} as any;

describe('Chrome Extension', () => {
  let modal: HTMLElement;

  beforeEach(() => {
    // Create a fresh document body before each test
    document.body.innerHTML = '';
    markAsRrwebTest();
  });

  afterEach(() => {
    // Clean up after each test
    if (modal) {
      removeTestModal(modal);
    }
    // Remove any markers
    const marker = document.getElementById('allow-button-clicked-marker');
    if (marker && marker.parentNode) {
      marker.parentNode.removeChild(marker);
    }
  });

  it('should detect rrweb replay environment', () => {
    // Create rrweb replay elements
    const replayEl = document.createElement('div');
    replayEl.id = 'replay';
    document.body.appendChild(replayEl);

    expect(checkIfRrwebReplay()).toBe(true);
  });

  it('should detect test environment via data attribute', () => {
    // Mark as test already done in beforeEach
    expect(checkIfRrwebReplay()).toBe(true);
  });

  it('should find and mark the allow button in a test modal', () => {
    // Create a test modal with an Allow button
    modal = createTestModal();

    // Trigger the find and click function
    findAndClickAllowButton();

    // Check if the button was "clicked" (marked in test mode)
    const buttonText = checkAllowButtonClicked();
    expect(buttonText).toBe('Allow for this chat');
  });

  it('should not do anything when no modal is present', () => {
    // Don't create a modal

    // Trigger the find and click function
    findAndClickAllowButton();

    // Check that no button was "clicked"
    const buttonText = checkAllowButtonClicked();
    expect(buttonText).toBeNull();
  });

  it('should not do anything when modal has no allow button', () => {
    // Create a modal without an allow button
    modal = document.createElement('div');
    modal.className = 'z-modal';

    const button = document.createElement('button');
    button.textContent = 'Some other button';

    modal.appendChild(button);
    document.body.appendChild(modal);

    // Trigger the find and click function
    findAndClickAllowButton();

    // Check that no button was "clicked"
    const buttonText = checkAllowButtonClicked();
    expect(buttonText).toBeNull();
  });
});
