// Background script for the Chrome extension
// This script runs in the background and only handles initialization
console.log('Background script loaded');

// Add listener for extension installation
chrome.runtime.onInstalled.addListener(() => {
  console.log('Extension installed');
});

export {};
