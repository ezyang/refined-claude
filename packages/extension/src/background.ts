// Background script for the Chrome extension
// This script runs in the background and handles initialization and messaging
console.log('Background script loaded');

// Add listener for extension installation
chrome.runtime.onInstalled.addListener(() => {
  console.log('Extension installed');

  // Initialize default settings
  chrome.storage.sync.get({ autoContinueEnabled: true }, result => {
    if (chrome.runtime.lastError) {
      console.error('Error loading settings:', chrome.runtime.lastError);
      return;
    }

    // If the setting doesn't exist yet, initialize it
    if (result.autoContinueEnabled === undefined) {
      chrome.storage.sync.set({ autoContinueEnabled: true }, () => {
        if (chrome.runtime.lastError) {
          console.error('Error saving default settings:', chrome.runtime.lastError);
          return;
        }
        console.log('Default settings initialized:', { autoContinueEnabled: true });
      });
    } else {
      console.log('Existing settings found:', result);
    }
  });

  // Request permissions for notifications
  chrome.permissions.contains({ permissions: ['notifications'] }, hasPermission => {
    if (!hasPermission) {
      console.log('Requesting notification permission');
      chrome.permissions.request({ permissions: ['notifications'] }, granted => {
        console.log('Notification permission granted:', granted);
      });
    }
  });
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

  if (message.action === 'showNotification') {
    // Show notification using Chrome's notification API
    const { title, message: notificationMessage } = message;

    console.log('Showing notification:', title, notificationMessage);

    const icon_url = chrome.runtime.getURL('images/icon128.png');
    console.log('icon url:', icon_url);

    chrome.notifications.create({
      type: 'basic',
      iconUrl: icon_url,
      title: title || 'Claude Notification',
      message: notificationMessage || 'Notification from Claude',
      priority: 1,
    });

    // No response needed
    sendResponse({ success: true });
    return true;
  }

  if (message.action === 'injectScriptIntoFrame') {
    const { tabId, frameSelector } = message;
    if (!tabId || !frameSelector) {
      sendResponse({ error: 'Missing required parameters' });
      return true;
    }

    // First, inject a content script into all frames to find the one with the desired selector
    chrome.scripting
      .executeScript({
        target: { tabId, allFrames: true },
        func: selector => {
          // Check if this frame has an element with the selector or is the frame itself
          const hasSelector =
            selector === 'self' ||
            (window.frameElement &&
              window.frameElement.getAttribute('data-extension-frame-id') === selector);

          // Return true if this is the target frame, along with the frameId
          return {
            isTargetFrame: hasSelector,
            url: window.location.href,
          };
        },
        args: [frameSelector],
      })
      .then(results => {
        // Find the frame that returned true for having the selector
        const targetFrame = results.find(result => result.result && result.result.isTargetFrame);

        if (!targetFrame) {
          sendResponse({ error: 'Frame selector invalid' });
          return;
        }

        const frameId = targetFrame.frameId;

        // Execute script in the identified frame
        chrome.scripting
          .executeScript({
            target: { tabId, frameIds: [frameId] },
            files: ['index.global.js'],
          })
          .then(results => {
            console.log('Script injection results:', results);
            sendResponse({ success: true, results });
          })
          .catch(error => {
            console.error('Script injection error:', error);
            sendResponse({ error: error.message });
          });
      })
      .catch(error => {
        console.error('Frame detection error:', error);
        sendResponse({ error: `Frame detection failed: ${error.message}` });
      });

    return true; // Keep the message channel open for the async response
  }
});

// Export explicitly as an ES module - this helps bundlers understand it's an ES module
const exported = {};
export default exported;
