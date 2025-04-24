// Background script for the Chrome extension
// This script runs in the background and handles initialization and messaging
console.log('Background script loaded');

// Reference the global type definitions
/// <reference path="./utils/global.d.ts" />

// Add listener for extension installation
chrome.runtime.onInstalled.addListener(() => {
  console.log('Extension installed');
});

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Received message:', message, 'from:', sender);

  if (message.action === 'getTabInfo') {
    // Return the sender's tab ID
    if (sender.tab && sender.tab.id) {
      sendResponse({ tabId: sender.tab.id });
    } else {
      sendResponse({ error: 'Tab ID not available' });
    }
    return true; // Keep the message channel open for the async response
  }

  if (message.action === 'injectScriptIntoFrame') {
    const { tabId, frameSelector } = message;
    if (!tabId || !frameSelector) {
      sendResponse({ error: 'Missing required parameters' });
      return true;
    }

    // First inject our shared module into the frame
    chrome.scripting.executeScript({
      target: { tabId, allFrames: true },
      files: ['modalObserver.js']  // Path relative to extension root in the built output
    })
    .then(() => {
      // Then inject our frame selector script that uses the shared module
      return chrome.scripting.executeScript({
        target: { tabId, allFrames: true },
        func: executeInTargetFrame,
        args: [frameSelector]
      });
    })
    .then(results => {
      console.log('Script injection results:', results);
      sendResponse({ success: true, results });
    })
    .catch(error => {
      console.error('Script injection error:', error);
      sendResponse({ error: error.message });
    });

    return true; // Keep the message channel open for the async response
  }
});

// Function to execute in target frames
function executeInTargetFrame(frameSelector: string): boolean {
  // This code runs in each frame
  // Check if this is the target frame by checking if our parent has the marker
  // or if we are directly the target frame
  if (frameSelector === 'self' ||
      (window.frameElement && window.frameElement.getAttribute('data-extension-frame-id') === frameSelector)) {

    console.log('[I-CONTENT] Target frame identified, setting up modal observer');

    // We expect the modalObserver module to be already injected
    if (typeof window.findAndClickAllowButton === 'function' &&
        typeof window.setupModalObserver === 'function') {

      // Check for existing modals first
      window.findAndClickAllowButton(false, '[I-CONTENT]');

      // Set up observer for future modals
      window.setupModalObserver(
        () => window.findAndClickAllowButton(false, '[I-CONTENT]'),
        '[I-CONTENT]'
      );

      // Add a marker to avoid duplicate executions
      if (!document.querySelector('#sublime-claude-content-script-injected')) {
        const marker = document.createElement('div');
        marker.id = 'sublime-claude-content-script-injected';
        marker.style.display = 'none';
        document.head.appendChild(marker);
      }

      return true; // Successfully executed in target frame
    } else {
      console.error('[I-CONTENT] Modal observer module not found');
      return false;
    }
  }

  return false; // Not the target frame
}

// Export explicitly as an ES module - this helps bundlers understand it's an ES module
const exported = {};
export default exported;
