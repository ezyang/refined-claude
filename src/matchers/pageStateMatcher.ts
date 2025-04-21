/**
 * A simplified implementation of Chrome's PageStateMatcher
 * Used to test rule matching against DOM without a full browser environment
 */
export class PageStateMatcher {
  private cssSelectors: string[];

  constructor(options: { css?: string[] }) {
    this.cssSelectors = options.css || [];
  }

  /**
   * Checks if the current document matches the PageStateMatcher criteria
   * @param document The document to check against
   * @returns boolean indicating whether the matcher matches
   */
  public matches(document: any): boolean {
    // If no CSS selectors were provided, assume it's not a match
    if (!this.cssSelectors || this.cssSelectors.length === 0) {
      return false;
    }

    // Check if any of the CSS selectors match
    return this.cssSelectors.some(selector => {
      try {
        const elements = document.querySelectorAll(selector);
        return elements.length > 0;
      } catch (e) {
        console.error(`Invalid CSS selector: ${selector}`, e);
        return false;
      }
    });
  }
}

/**
 * Mock implementation of chrome.declarativeContent
 * Just enough to support the specific matcher and rule structure
 */
export const declarativeContent = {
  PageStateMatcher,
  ShowAction: class ShowAction {
    // Empty implementation - we don't need to actually implement actions for the test
  }
};
