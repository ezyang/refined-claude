/**
 * Defines rules for detecting specific dialog elements
 * This module can be shared between the Chrome extension and testing code
 */

// We need to handle the case where this is imported in a browser context (chrome exists)
// or in a Node.js testing context (chrome doesn't exist)
declare const chrome: any;

// Define a type for our rule structure
export interface DialogRule {
  id: string;
  conditions: any[];
  actions: any[];
}

/**
 * Creates the rule for detecting the "Allow tool from" dialog
 * This function works in both browser and testing environments
 * @param declarativeContent The declarativeContent object (either from chrome or our mock)
 * @returns The rule object for detecting the dialog
 */
export function createAllowToolDialogRule(declarativeContent: any): DialogRule {
  return {
    // Unique ID for the rule
    id: "detectAllowToolDialogRule",
    // Conditions that must be met
    conditions: [
      new declarativeContent.PageStateMatcher({
        // CSS selector to match the dialog
        css: ["dialog[name^='Allow tool from']"],
      })
    ],
    // Actions to take when conditions are met
    actions: [
      // Show the extension's action icon (defined in manifest.json)
      new declarativeContent.ShowAction()
    ]
  };
}

/**
 * In a browser context, this will be the actual chrome.declarativeContent
 * In a testing context, this will be our mock implementation
 */
export function getDeclarativeContent() {
  // If we're in a browser context with Chrome APIs available
  if (typeof chrome !== 'undefined' && chrome.declarativeContent) {
    return chrome.declarativeContent;
  }

  // In testing context, we'll import our mock implementation
  // We need to do this dynamically to avoid errors in browser context
  const { declarativeContent } = require('./matchers/pageStateMatcher');
  return declarativeContent;
}

/**
 * Gets the rule using the appropriate declarativeContent implementation
 * This is the main function that should be used by both extension and tests
 */
export function getAllowToolDialogRule(): DialogRule {
  const declarativeContent = getDeclarativeContent();
  return createAllowToolDialogRule(declarativeContent);
}
