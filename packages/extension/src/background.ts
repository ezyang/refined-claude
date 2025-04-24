// Background script for the Chrome extension
// This script runs in the background and handles initialization and messaging
console.log('Background script loaded');

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

    let frameId: number | undefined;
    chrome.webNavigation.getAllFrames({ tabId }, (frames) => {
      if (frames) {
        for (const frame of frames) {
          if (frame.getAttribute('data-extension-frame-id', frameSelector)) {
            frameId = frame.frameId;
          }
        }
      }
    });

    if (frameId === undefined) {
      sendResponse({error: 'Frame selector invalid'});
      return true;
    }

    // Execute script in the specified frame
    chrome.scripting.executeScript({
      target: { tabId, frameIds: [frameId] },
      files: ["index.global.js"],
    }).then(results => {
      console.log('Script injection results:', results);
      sendResponse({ success: true, results });
    }).catch(error => {
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

    // Function to find and click the "Allow for this chat" button
    function findAndClickAllowButton(): void {
      const modal = document.querySelector('.z-modal');
      if (!modal) return;

      console.log('[I-CONTENT] Found z-modal in iframe:', modal);

      const allowButton = Array.from(modal.querySelectorAll('button'))
        .find(button => button.textContent?.includes('Allow for this chat'));

      if (allowButton) {
        console.log('[I-CONTENT] Found "Allow for this chat" button in iframe:', allowButton);
        console.log('[I-CONTENT] Clicking "Allow for this chat" button in iframe');
        allowButton.click();
      } else {
        console.log('[I-CONTENT] Could not find "Allow for this chat" button in modal in iframe');
      }
    }

    // Set up observer for modal elements
    function setupModalObserver(): void {
      const observer = new MutationObserver((mutations) => {
        const shouldCheck = mutations.some(mutation => {
          if (mutation.addedNodes.length > 0) {
            for (const node of Array.from(mutation.addedNodes)) {
              if (node instanceof HTMLElement) {
                if (node.classList?.contains('z-modal') || node.querySelector('.z-modal')) {
                  return true;
                }
              }
            }
          }

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

      observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['class']
      });

      console.log('[I-CONTENT] Modal observer set up in iframe');
    }

    // Check for existing modals first
    findAndClickAllowButton();

    // Set up observer for future modals
    setupModalObserver();

    // Add a marker to avoid duplicate executions
    if (!document.querySelector('#sublime-claude-content-script-injected')) {
      const marker = document.createElement('div');
      marker.id = 'sublime-claude-content-script-injected';
      marker.style.display = 'none';
      document.head.appendChild(marker);
    }

    return true; // Successfully executed in target frame
  }

  return false; // Not the target frame
}

// Export explicitly as an ES module - this helps bundlers understand it's an ES module
const exported = {};
export default exported;
