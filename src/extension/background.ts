/**
 * Background script for the Chrome extension
 * Sets up the rule to detect the "Allow tool from" dialog
 */

import { getAllowToolDialogRule } from '../rules';

// Listen for extension installation or update
chrome.runtime.onInstalled.addListener(() => {
  // Remove any existing rules
  chrome.declarativeContent.onPageChanged.removeRules(undefined, () => {
    // Add our rule to detect the "Allow tool from" dialog
    const rule = getAllowToolDialogRule();

    // Register the rule with Chrome
    chrome.declarativeContent.onPageChanged.addRules([rule]);

    console.log('Registered rule:', rule.id);
  });
});
